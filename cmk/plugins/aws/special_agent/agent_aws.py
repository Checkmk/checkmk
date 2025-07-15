#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Amazon web services (AWS) with Check_MK.
"""

# TODO: Using BaseClient all over the place is wrong and leads to the tons of ignore[attr-defined]
# suppressions below. The code and types have to be restructured to use the right subclass of
# BaseClient for the client in question.

import abc
import argparse
import hashlib
import itertools
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, StrEnum
from pathlib import Path
from time import sleep
from typing import (
    Any,
    assert_never,
    Literal,
    NamedTuple,
    NotRequired,
    TYPE_CHECKING,
    TypedDict,
    TypeVar,
)

import boto3
import botocore
from botocore.client import BaseClient
from pydantic import BaseModel, ConfigDict, Field

from cmk.ccc import store
from cmk.ccc.exceptions import MKException

from cmk.utils import password_store
from cmk.utils.paths import tmp_dir

from cmk.plugins.aws.constants import (  # pylint: disable=cmk-module-layer-violation
    AWSEC2InstFamilies,
    AWSEC2InstTypes,
    AWSEC2LimitsDefault,
    AWSEC2LimitsSpecial,
    AWSECSQuotaDefaults,
    AWSElastiCacheQuotaDefaults,
    AWSRegions,
)
from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args
from cmk.special_agents.v0_unstable.misc import (
    DataCache,
    datetime_serializer,
    get_seconds_since_midnight,
    vcrtrace,
)

if TYPE_CHECKING:
    from mypy_boto3_logs.client import CloudWatchLogsClient

NOW = datetime.now()

AWSStrings = bytes | str


Dimension = Mapping[Literal["Name", "Value"], str | None]


class MetricData(TypedDict):
    Namespace: str
    MetricName: str
    Dimensions: Sequence[Dimension]


class MetricStat(TypedDict):
    Metric: MetricData
    Period: int
    Stat: str
    Unit: NotRequired[str]


class MetricRequired(TypedDict):
    Id: str
    Label: str


class Metric(MetricRequired, total=False):
    Expression: str
    MetricStat: MetricStat
    Period: int


Metrics = list[Metric]


class RawTag(TypedDict):
    Name: str
    Values: Sequence[str]


OverallTags = tuple[Sequence[str] | None, Sequence[str] | None]
RawTags = list[RawTag]
Tags = list[Mapping[Literal["Key", "Value"], str]]

Scope = Literal["REGIONAL", "CLOUDFRONT"]
LoadBalancers = dict[str, list[tuple[str, Sequence[str]]]]
Buckets = Sequence[Mapping[Literal["Name", "CreationDate"], str | datetime]]
Results = dict[tuple[str, float, float], Sequence["AWSSectionResult"]]

T = TypeVar("T")


class Quota(BaseModel):
    QuotaName: str
    Value: float


class NamingConvention(Enum):
    ip_region_instance = "ip_region_instance"
    private_dns_name = "private_dns_name"


class Instance(BaseModel):
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    private_dns_name: str | None = Field(None, alias="PrivateDnsName")
    instance_id: str = Field(..., alias="InstanceId")


class TagsImportPatternOption(Enum):
    ignore_all = "IGNORE_ALL"
    import_all = "IMPORT_ALL"


TagsOption = str | Literal[TagsImportPatternOption.ignore_all, TagsImportPatternOption.import_all]


# TODO
# Rewrite API calls from low-level client to high-level resource:
# Boto3 has two distinct levels of APIs. Client (or "low-level") APIs provide
# one-to-one mappings to the underlying HTTP API operations. Resource APIs hide
# explicit network calls but instead provide resource objects and collections to
# access attributes and perform actions.

# Note that in this case you do not have to make a second API call to get the
# objects; they're available to you as a collection on the bucket. These
# collections of subresources are lazily-loaded.

# TODO limits
# - per account (S3)
# - per region (EC2, EBS, ELB, RDS)

# TODO network load balancers
# - gather the metrics HealthyHostCount and UnHealthyHostCount using the correct dimensions (load
#   balancer and target group)

#   .--overview------------------------------------------------------------.
#   |                                        _                             |
#   |               _____   _____ _ ____   _(_) _____      __              |
#   |              / _ \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /              |
#   |             | (_) \ V /  __/ |   \ V /| |  __/\ V  V /               |
#   |              \___/ \_/ \___|_|    \_/ |_|\___| \_/\_/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Overview of sections and dependencies                                |
#   '----------------------------------------------------------------------'

# CostsAndUsage

# ReservationUtilization

# EC2Limits
# |
# '-- EC2Summary
#     |
#     |-- EC2Labels
#     |
#     |-- EC2SecurityGroups
#     |
#     '-- EC2

# EBSLimits,EC2Summary
# |
# '-- EBSSummary
#     |
#     '-- EBS

# S3Limits
# |
# '-- S3Summary
#     |
#     |-- S3
#     |
#     '-- S3Requests

# GlacierLimits
# |
# '-- Glacier

# ELBLimits
# |
# '-- ELBSummaryGeneric
#     |
#     |-- ELBLabelsGeneric
#     |
#     |-- ELBHealth
#     |
#     '-- ELB

# ELBv2Limits
# |
# '-- ELBSummaryGeneric
#     |
#     |-- ELBLabelsGeneric
#     |
#     |-- ELBv2TargetGroups
#     |
#     '-- ELBv2Application, ELBv2ApplicationTargetGroupsHTTP, ELBv2ApplicationTargetGroupsLambda, ELBv2Network

# RDSLimits

# RDSSummary
# |
# '-- RDS

# CloudFrontSummary
# |
# '-- CloudFront

# CloudwatchAlarmsLimits
# |
# '-- CloudwatchAlarms

# DynamoDBLimits
# |
# '-- DynamoDBSummary
#     |
#     '-- DynamoDBTable

# WAFV2Limits
# |
# '-- WAFV2Summary
#     |
#     '-- WAFV2WebACL

# LambdaSummary, LambdaRegionLimits
# |
# '-- LambdaProvisionedConcurrency
#     |
#     |-- LambdaCloudwatch
#     |
#     '-- LambdaCloudwatchInsights

# Route53HealthChecks
# |
# '-- Route53Cloudwatch

# SNSLimits
# |
# |-- SNSSMS
# |
# '-- SNSSummary
#     |
#     '-- SNS

# ECSLimits
# |
# '-- ECSSummary
#     |
#     '-- ECS

# ElastiCacheLimits
# |
# '-- ElastiCacheSummary
#     |
#     '-- ElastiCache


class AWSConfig:
    def __init__(
        self,
        hostname: str,
        sys_argv: Args,
        overall_tags: OverallTags,
        piggyback_naming_convention: NamingConvention,
        tags_option: TagsOption = TagsImportPatternOption.import_all,
    ) -> None:
        self.hostname = hostname
        self._overall_tags = self._prepare_tags(overall_tags)
        self.service_config: dict = {}
        self._config_hash_file = AWSCacheFilePath / ("%s.config_hash" % hostname)
        self._current_config_hash = self._compute_config_hash(sys_argv)
        self.piggyback_naming_convention = piggyback_naming_convention
        self.tags_option = tags_option

    def add_service_tags(self, tags_key: str, tags: OverallTags) -> None:
        """Convert commandline input
        from
            ([['foo'], ['aaa'], ...], [['bar', 'baz'], ['bbb', 'ccc'], ...])
        to
            Filters=[{'Name': 'tag:foo', 'Values': ['bar', 'baz']},
                     {'Name': 'tag:aaa', 'Values': ['bbb', 'ccc']}, ...]
        as we need in API methods if and only if keys AND values are set.
        """
        self.service_config.setdefault(tags_key, None)
        keys, values = tags
        if keys and values:
            self.service_config[tags_key] = self._prepare_tags(tags)
        elif self._overall_tags:
            self.service_config[tags_key] = self._overall_tags

    @staticmethod
    def _prepare_tags(
        tags: OverallTags,
    ) -> RawTags | None:
        keys, values = tags
        if keys is None or values is None:
            return None

        return [{"Name": "tag:%s" % k, "Values": v} for k, v in zip([k[0] for k in keys], values)]

    def add_single_service_config(self, key: str, value: object | None) -> None:
        self.service_config.setdefault(key, value)

    @staticmethod
    def _compute_config_hash(sys_argv: Args) -> str:
        filtered_sys_argv = dict(
            filter(lambda el: el[0] not in ["debug", "verbose", "no_cache"], vars(sys_argv).items())
        )

        # Be careful to use a hashing mechanism that generates the same hash across
        # different python processes! Otherwise the config file will always be
        # out-of-date
        return hashlib.sha256("".join(sorted(filtered_sys_argv)).encode()).hexdigest()

    def is_up_to_date(self) -> bool:
        old_config_hash = self._load_config_hash()
        if old_config_hash is None:
            logging.info(
                "AWSConfig: %s: New config: '%s'", self.hostname, self._current_config_hash
            )
            self._write_config_hash()
            return False

        if old_config_hash != self._current_config_hash:
            logging.info(
                "AWSConfig: %s: Config has changed: '%s' -> '%s'",
                self.hostname,
                old_config_hash,
                self._current_config_hash,
            )
            self._write_config_hash()
            return False

        logging.info(
            "AWSConfig: %s: Config is up-to-date: '%s'", self.hostname, self._current_config_hash
        )
        return True

    def _load_config_hash(self) -> str | None:
        try:
            with self._config_hash_file.open(mode="r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def _write_config_hash(self) -> None:
        store.save_text_to_file(self._config_hash_file, f"{self._current_config_hash}\n")


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _chunks(list_: Sequence[T], length: int = 100) -> Sequence[Sequence[T]]:
    return [list_[i : i + length] for i in range(0, len(list_), length)]


def _get_ec2_piggyback_hostname(
    piggyback_naming_convention: NamingConvention, inst: Mapping[str, object], region: str
) -> str | None:
    # PrivateIpAddress and InstanceId is available although the instance is stopped
    # When we terminate an instance, the instance gets the state "terminated":
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
    # The instance remains in this state about 60 minutes, after 60 minutes the
    # instance is no longer visible in the console.
    # In this case we do not deliever any data for this piggybacked host such that
    # the services go stable and Check_MK service reports "CRIT - Got not information".
    parsed_instance = Instance.model_validate(inst)
    match piggyback_naming_convention:
        case NamingConvention.private_dns_name:
            return parsed_instance.private_dns_name
        case NamingConvention.ip_region_instance:
            if parsed_instance.private_ip_address and parsed_instance.instance_id:
                return (
                    f"{parsed_instance.private_ip_address}-{region}-{parsed_instance.instance_id}"
                )
            return None
        case _:
            assert_never(piggyback_naming_convention)


def _hostname_from_name_and_region(name: str, region: str) -> str:
    """
    We add the region to the the hostname because resources in different regions might have the
    same names (for example replicated DynamoDB tables).
    """
    return f"{name}_{region}"


def _elbv2_load_balancer_arn_to_dim(arn: str) -> str:
    # for application load balancers:
    # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/load-balancer-name/load-balancer-id
    # We need: app/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
    # for network load balancers:
    # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/net/load-balancer-name/load-balancer-id
    # We need: net/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
    return "/".join(arn.split("/")[-3:])


def _elbv2_target_group_arn_to_dim(arn: str) -> str:
    return arn.split(":")[-1]


def _get_table_names(client: BaseClient, get_response_content: Callable) -> Iterable[str]:
    for page in client.get_paginator("list_tables").paginate():
        yield from get_response_content(page, "TableNames")


def _describe_dynamodb_tables(
    client: BaseClient,
    get_response_content: Callable,
    fetched_table_names: Sequence[str] | None = None,
) -> Sequence[dict[str, object]]:
    table_names = (
        fetched_table_names
        if fetched_table_names is not None
        else _get_table_names(client, get_response_content)
    )

    tables = []
    for table_name in table_names:
        try:
            tables.append(
                get_response_content(client.describe_table(TableName=table_name), "Table")  # type: ignore[attr-defined]
            )
        # NOTE: The suppression below is needed because of BaseClientExceptions.__getattr__ magic.
        except client.exceptions.ResourceNotFoundException:  # type: ignore[misc]
            # we raise the exception if we fetched the table names from the API, since in that case
            # all tables should exist, otherwise something went really wrong
            if fetched_table_names is None:
                raise

    return tables


def _validate_wafv2_scope_and_region(scope: Scope, region: str) -> str:
    """
    WAFs can either be deployed locally, for example in front of Application Load Balancers,
    or globally, in front of CloudFront. The global ones can only be queried from the region
    us-east-1.
    """

    if scope == "CLOUDFRONT":
        assert region == "us-east-1", (
            "The scope of WAFV2Limits / WAFV2Summary  can only be set to 'CLOUDFRONT' when using "
            "the region us-east-1, other combinations crash the wafv2 client"
        )
        region_report = "CloudFront"
    else:
        region_report = region

    return region_report


def _iterate_through_wafv2_list_operations(
    list_operation: Callable, scope: str, entry_name: str, get_response_content: Callable
) -> Sequence:
    """
    For some reason, the return objects of the list_... functions of the WAFV2-client seem to
    always contain 'NextMarker', indicating that there are more values to retrieve, even if there
    are not. Also, these functions cannot be paginated.
    """

    response = list_operation(Scope=scope)
    results = get_response_content(response, entry_name)
    next_marker = get_response_content(response, "NextMarker", dflt="")

    while next_marker:
        response = list_operation(NextMarker=next_marker, Scope=scope)
        results.extend(get_response_content(response, entry_name))
        next_marker = get_response_content(response, "NextMarker", dflt="")

    return results


def _get_wafv2_web_acls(
    client: BaseClient,
    scope: str,
    get_response_content: Callable,
    web_acls_info: Sequence[Mapping[str, str]] | None = None,
    web_acls_names: Sequence[str] | None = None,
) -> Sequence[dict[str, object]]:
    if web_acls_info is None:
        web_acls_info = _iterate_through_wafv2_list_operations(
            client.list_web_acls,  # type: ignore[attr-defined]
            scope,
            "WebACLs",
            get_response_content,
        )

    if web_acls_names is not None:
        web_acls_info = [
            web_acl_info for web_acl_info in web_acls_info if web_acl_info["Name"] in web_acls_names
        ]

    web_acls = [
        get_response_content(
            client.get_web_acl(Name=web_acl_info["Name"], Scope=scope, Id=web_acl_info["Id"]),  # type: ignore[attr-defined]
            "WebACL",
        )
        for web_acl_info in web_acls_info
    ]

    def _convert_byte_match_statement(byte_match_statement: dict[str, Any]) -> None:
        byte_match_statement["SearchString"] = byte_match_statement["SearchString"].decode()

    def _byte_convert_statement(general_statement: dict[str, Any]) -> None:
        for statement_item in general_statement.items():
            match statement_item:
                case ("ByteMatchStatement", statement):
                    _convert_byte_match_statement(statement)
                case (
                    "RateBasedStatement" | "NotStatement",
                    {"ScopeDownStatement": {"ByteMatchStatement": statement}},
                ):
                    _convert_byte_match_statement(statement)
                case ("AndStatement" | "OrStatement", statement):
                    for s in statement["Statements"]:
                        _byte_convert_statement(s)
                case _:
                    pass

    for acl in web_acls:
        for rule in acl["Rules"]:
            _byte_convert_statement(rule["Statement"])

    return web_acls


ResourceTags = Mapping[str, Tags]


def fetch_resource_tags_from_types(
    tagging_client: BaseClient, resource_type_filters: Sequence[str]
) -> ResourceTags:
    """Returns all the resources in the region that have tags.

    This is useful when the service-specific API is not returning tags for every resource as this
    allows you to get all the tags with a single API call rather than calling get_tags for every
    resource.

    For example, the CloudFront APIs don't allow to get tags for all the distributions and the only
    way to have the tags would be to call the `list_tags_for_resource` API for every single
    distribution.
    To prevent that, we can call this method with
    `resource_type_filters=['cloudfront:distribution']` and with the tags you want to filter.

    More info on the format of the resources type on the underlying API call documentation:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/resourcegroupstaggingapi.html#ResourceGroupsTaggingAPI.Client.get_resources
    """

    tagged_resources = []
    # The get_resource API call has a matching rule (AND) different than the one that we use in
    # checkmk (OR) so we need to fetch all the resources containing tags first and then apply our
    # matching rule.
    # We are calling it with empty `TagFilter` param so get every resource that ever had a tag.
    # For the tags matching rules or other info, look at the documentation of the API call:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/resourcegroupstaggingapi.html#ResourceGroupsTaggingAPI.Client.get_resources
    for page in tagging_client.get_paginator("get_resources").paginate(
        TagFilters=[],
        ResourceTypeFilters=resource_type_filters,
    ):
        tagged_resources.extend(page.get("ResourceTagMappingList", []))

    return {r["ResourceARN"]: r["Tags"] for r in tagged_resources}


def filter_resources_matching_tags(
    tagged_resources: ResourceTags,
    tags_to_match: Tags,
) -> set[str]:
    """Returns the ARN of all the resources in the region that match **ANY** of the provided tags.

    This is useful when the service-specific API is not returning tags for every resource as this
    allows you to get all the tags with a single API call (e.g., fetch_resource_tags_from_types)
    and filter them with this function.
    """

    if not tags_to_match:
        return set()

    tags_to_match_by_id = defaultdict(set)
    for curr_tag in tags_to_match:
        tags_to_match_by_id[curr_tag["Key"]].add(curr_tag["Value"])

    matching_resources_arn = set()
    for resource_arn, resource_tags in tagged_resources.items():
        is_any_tag_matching = any(
            curr_tag["Key"] in tags_to_match_by_id
            and curr_tag["Value"] in tags_to_match_by_id[curr_tag["Key"]]
            for curr_tag in resource_tags
        )
        if is_any_tag_matching:
            matching_resources_arn.add(resource_arn)
    return matching_resources_arn


def _describe_alarms(
    client: BaseClient, get_response_content: Callable, names: Sequence[str] | None = None
) -> Iterator[Mapping[str, object]]:
    paginator = client.get_paginator("describe_alarms")
    kwargs = {"AlarmNames": names} if names else {}

    for page in paginator.paginate(**kwargs):
        yield from get_response_content(page, "MetricAlarms")


# .
#   .--section API---------------------------------------------------------.
#   |                       _   _                  _    ____ ___           |
#   |         ___  ___  ___| |_(_) ___  _ __      / \  |  _ \_ _|          |
#   |        / __|/ _ \/ __| __| |/ _ \| '_ \    / _ \ | |_) | |           |
#   |        \__ \  __/ (__| |_| | (_) | | | |  / ___ \|  __/| |           |
#   |        |___/\___|\___|\__|_|\___/|_| |_| /_/   \_\_|  |___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---result distributor---------------------------------------------------


class ResultDistributor:
    """
    Mediator which distributes results from sections
    in order to reduce queries to AWS account.
    """

    def __init__(self) -> None:
        self._colleagues: dict[str, list[AWSSection]] = defaultdict(list)

    def add(self, sender_name: str, colleague: "AWSSection") -> None:
        self._colleagues[sender_name].append(colleague)

    def distribute(self, sender: "AWSSection", result: "AWSComputedContent") -> None:
        for colleague in self._colleagues[sender.name]:
            if colleague.name != sender.name:
                colleague.receive(sender, result)


class ResultDistributorS3Limits(ResultDistributor):
    """
    Special mediator for distributing results from S3Limits. This mediator stores any received
    results and distributes both upon receiving and upon adding a new colleague. This is done
    because we want to run S3Limits only once (does not matter for which region, results are the
    same for all regions) and later distribute the results to S3Summary objects in other regions.
    """

    def __init__(self) -> None:
        super().__init__()
        self._received_results: dict = {}

    def add(self, sender_name: str, colleague: "AWSSection") -> None:
        super().add(sender_name, colleague)
        for sender, content in self._received_results.values():
            colleague.receive(sender, content)

    def distribute(self, sender: "AWSSection", result: "AWSComputedContent") -> None:
        self._received_results.setdefault(sender.name, (sender, result))
        super().distribute(sender, result)

    def is_empty(self) -> bool:
        return len(self._colleagues) == 0


#   ---sections/colleagues--------------------------------------------------


class AWSSectionResults(NamedTuple):
    results: list
    cache_timestamp: float


class AWSSectionResult(NamedTuple):
    piggyback_hostname: AWSStrings
    content: Any
    piggyback_host_labels: Mapping[str, str] | None = None


class AWSLimit(NamedTuple):
    key: AWSStrings
    title: AWSStrings
    limit: int
    amount: int


class AWSRegionLimit(NamedTuple):
    key: AWSStrings
    title: AWSStrings
    limit: int
    amount: int
    region: AWSStrings


class AWSColleagueContents(NamedTuple):
    content: Any
    cache_timestamp: float


class AWSRawContent(NamedTuple):
    content: Any
    cache_timestamp: float


class AWSComputedContent(NamedTuple):
    content: Any
    cache_timestamp: float


AWSCacheFilePath = tmp_dir / "agents" / "agent_aws"


class AWSSection(DataCache):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        cache_dir = AWSCacheFilePath / region / config.hostname
        super().__init__(cache_dir, self.name)
        self._client = client
        self._region = region
        self._config = config
        self._distributor = ResultDistributor() if distributor is None else distributor
        self._received_results: dict[str, Any] = {}

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def cache_interval(self) -> int:
        """
        In general the default resolution of AWS metrics is 5 min (300 sec)
        The default resolution of AWS S3 metrics is 1 day (86400 sec)
        We use interval property for cached section.
        """
        raise NotImplementedError

    @property
    def region(self) -> str:
        return self._region

    @property
    def granularity(self) -> int:
        """
        The granularity of the returned data in seconds.
        """
        raise NotImplementedError

    @property
    def period(self) -> int:
        return self.validate_period(2 * self.granularity)

    @staticmethod
    def validate_period(period: int, resolution_type: str = "low") -> int:
        """
        What this is all about:
        https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricStat.html
        >>> [AWSSection.validate_period(p, r) for p, r in [(34, "low"), (45, "high"), (120.0, "low")]]
        Traceback (most recent call last):
        ...
        AssertionError: Period must be a multiple of 60 or equal to 1, 5, 10, 30, 60 in case of high resolution.

        >>> AWSSection.validate_period(1234, resolution_type="foo bar")
        Traceback (most recent call last):
            ...
        ValueError: Unknown resolution type: 'foo bar'
        >>> AWSSection.validate_period(120)
        120
        >>> AWSSection.validate_period(30, "high")
        30
        >>> AWSSection.validate_period(180, "high")
        180
        """
        if not isinstance(period, int):
            raise AssertionError(f"Period must be an integer, got {type(period)}.")

        allowed_multiples = 60
        additional_allowed = []

        if resolution_type == "high":
            additional_allowed.extend([1, 5, 10, 30, 60])
        elif resolution_type != "low":
            raise ValueError("Unknown resolution type: '%s'" % resolution_type)

        if not (not period % allowed_multiples or period in additional_allowed):
            raise AssertionError(
                f"Period must be a multiple of {allowed_multiples} or equal to 1, 5, "
                f"10, 30, 60 in case of high resolution."
            )
        return period

    def _send(self, content: AWSComputedContent) -> None:
        self._distributor.distribute(self, content)

    def receive(self, sender: "AWSSection", content: "AWSComputedContent") -> None:
        self._received_results.setdefault(sender.name, content)

    def run(self, use_cache: bool = False) -> AWSSectionResults:
        colleague_contents = self._get_colleague_contents()

        raw_data = self.get_data(colleague_contents, use_cache=use_cache)
        raw_content = AWSRawContent(
            raw_data, self.cache_timestamp if use_cache else NOW.timestamp()
        )

        computed_content = self._compute_content(raw_content, colleague_contents)

        self._send(computed_content)
        created_results = self._create_results(computed_content)

        final_results = []
        for result in created_results:
            if not result.content:
                logging.info("%s: Result is empty or None", self.name)
                continue

            # In the related check plug-in aws.include we parse these results and
            # extend list of json-loaded results, except for labels sections.
            self._validate_result_content(result.content)

            final_results.append(result)
        return AWSSectionResults(final_results, computed_content.cache_timestamp)

    def get_validity_from_args(self, *args: AWSColleagueContents) -> bool:
        (colleague_contents,) = args
        my_cache_timestamp = self.cache_timestamp
        if my_cache_timestamp is None:
            return False
        if colleague_contents.cache_timestamp > my_cache_timestamp:
            logging.info("Colleague data is newer than cache file %s", self._cache_file)
            return False
        return True

    @abc.abstractmethod
    def _get_colleague_contents(self) -> AWSColleagueContents:
        """
        Receive section contents from colleagues. The results are stored in
        self._received_results: {<KEY>: AWSComputedContent}.
        The relation between two sections must be declared in the related
        distributor in advance to make this work.
        Use max. cache_timestamp of all received results for
        AWSColleagueContents.cache_timestamp
        """

    @abc.abstractmethod
    def get_live_data(self, *args):
        """
        Call API methods, eg. 'response = ec2_client.describe_instances()' and
        extract content from raw content.  Raw contents basically consist of
        two sub results:
        - 'ResponseMetadata'
        - '<KEY>'
        Return raw_result['<KEY>'].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        """
        Compute the final content of this section based on the raw content of
        this section and the content received from the optional colleague
        sections.
        """

    @abc.abstractmethod
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        pass

    def _get_response_content(self, response, key: str, dflt=None):  # type: ignore[no-untyped-def]
        if dflt is None:
            dflt = []
        try:
            return response[key]
        except KeyError:
            logging.info("%s: KeyError; Available keys are %s", self.name, response)
            return dflt

    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, list), "%s: Result content must be of type 'list'" % self.name

    @staticmethod
    def prepare_tags_for_api_response(tags: RawTags) -> Tags | None:
        """
        We need to change the format, in order to filter out instances with specific
        tags if and only if we already fetched instances, eg. by limits section.
        The format:
        [{'Key': KEY, 'Value': VALUE}, ...]
        """
        if not tags:
            return None
        prepared_tags: Tags = []
        for tag in tags:
            tag_name = tag["Name"]
            if tag_name.startswith("tag:"):
                tag_key = tag_name[4:]
            else:
                tag_key = tag_name
            prepared_tags.extend([{"Key": tag_key, "Value": v} for v in tag["Values"]])
        return prepared_tags

    def process_tags_for_cmk_labels(self, tags: Tags) -> Mapping[str, str]:
        """Filter tags that are imported as host/service labels in Checkmk.

        This should not be mixed up with the filtering of services by tags to limit
        the services being created from the agent output.

        By default, all AWS tags are written to the agent output. This function filters
        and transforms the agent output depending on the CLI args given to the agent.
        Inside Checkmk the tags are validated to meet the Checkmk label requirements
        and added as host labels to their respective piggyback host and/or as service
        labels to the respective service using the syntax 'cmk/aws/tag/{key}:{value}'.
        """
        if self._config.tags_option == TagsImportPatternOption.import_all:
            return {tag["Key"]: tag["Value"] for tag in tags}
        if self._config.tags_option == TagsImportPatternOption.ignore_all:
            return {}
        return {
            tag["Key"]: tag["Value"]
            for tag in tags
            if re.search(self._config.tags_option, tag["Key"])
        }


class AWSSectionLimits(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
        quota_client: BaseClient | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._quota_client = quota_client
        self._limits: dict = {}

    def _add_limit(
        self, piggyback_hostname: str, limit: AWSLimit, region: str | None = None
    ) -> None:
        if region is None:
            region = self._region

        self._limits.setdefault(piggyback_hostname, []).append(
            AWSRegionLimit(
                key=limit.key,
                title=limit.title,
                limit=limit.limit,
                amount=limit.amount,
                region=region,
            )
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, limits)
            for piggyback_hostname, limits in self._limits.items()
        ]

    def _iter_service_quotas(self, service_code: str) -> Iterator[Quota]:
        if self._quota_client is None:
            return

        paginator = self._quota_client.get_paginator("list_service_quotas")
        for page in paginator.paginate(ServiceCode=service_code):
            for quota in self._get_response_content(page, "Quotas"):
                yield Quota(**quota)


class AWSSectionLabels(AWSSection):
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        assert isinstance(computed_content.content, dict), (
            "%s: Computed result of Labels section must be of type 'dict'" % self.name
        )
        for pb in computed_content.content:
            assert pb, "%s: Piggyback host name is not allowed to be empty" % self.name
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]

    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


class AWSSectionCloudwatch(AWSSection):
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        end_time = NOW.timestamp()
        start_time = end_time - self.period
        metric_specs = self._get_metrics(colleague_contents)
        if not metric_specs:
            return []

        # A single GetMetricData call can include up to 100 MetricDataQuery structures
        # There's no pagination for this operation:
        # self._client.can_paginate('get_metric_data') = False
        raw_content = []
        for chunk in _chunks(metric_specs):
            if not chunk:
                continue
            response = self._client.get_metric_data(  # type: ignore[attr-defined]
                MetricDataQueries=chunk,
                StartTime=start_time,
                EndTime=end_time,
            )

            metrics = self._get_response_content(response, "MetricDataResults")
            if not metrics:
                continue
            raw_content.extend(metrics)

        self._extend_metrics_by_period(metric_specs, raw_content)

        return raw_content

    @abc.abstractmethod
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        pass

    @staticmethod
    def _create_id_for_metric_data_query(index: int, metric_name: str, *args: str) -> str:
        """
        ID field must be unique in a single call.
        The valid characters are letters, numbers, and underscore.
        The first character must be a lowercase letter.
        Regex: ^[a-z][a-zA-Z0-9_]*$
        """
        return "_".join(["id", str(index)] + list(args) + [metric_name])

    def _extend_metrics_by_period(self, metrics: Metrics, raw_content: list) -> None:
        """
        Extend the queried metric values by the corresponding time period. For metrics based on the
        "Sum" statistics, we add the actual time period which can then be used by the check plug-ins
        to compute a rate. For all other metrics, we add 'None', such that the metric values are
        always 2-tuples (value, period), where period is either an actual time period such as 600 s
        or None.
        """
        for metric_specs, metric_contents in zip(metrics, raw_content):
            metric_stat = metric_specs.get("MetricStat", {})
            if metric_stat.get("Stat") == "Sum":
                period = metric_stat["Period"]
            else:
                period = None
            metric_contents["Values"] = [(v, period) for v in metric_contents["Values"]]


# .
#   .--costs/usage---------------------------------------------------------.
#   |                      _          __                                   |
#   |         ___ ___  ___| |_ ___   / /   _ ___  __ _  __ _  ___          |
#   |        / __/ _ \/ __| __/ __| / / | | / __|/ _` |/ _` |/ _ \         |
#   |       | (_| (_) \__ \ |_\__ \/ /| |_| \__ \ (_| | (_| |  __/         |
#   |        \___\___/|___/\__|___/_/  \__,_|___/\__,_|\__, |\___|         |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

# Interval between 'Start' and 'End' must be a DateInterval. 'End' is exclusive.
# Example:
# 2017-01-01 - 2017-05-01; cost and usage data is retrieved from 2017-01-01 up
# to and including 2017-04-30 but not including 2017-05-01.
# The GetCostAndUsage operation supports DAILY | MONTHLY | HOURLY granularities.
# The GetReservationUtilization operation supports only DAILY and MONTHLY granularities.


class CostsAndUsage(AWSSection):
    @property
    def name(self) -> str:
        return "costs_and_usage"

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        granularity_name, granularity_interval = "DAILY", self.granularity
        fmt = "%Y-%m-%d"
        response = self._client.get_cost_and_usage(  # type: ignore[attr-defined]
            TimePeriod={
                "Start": datetime.strftime(NOW - timedelta(seconds=granularity_interval), fmt),
                "End": datetime.strftime(NOW, fmt),
            },
            Granularity=granularity_name,
            Metrics=["UnblendedCost"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
                {"Type": "DIMENSION", "Key": "SERVICE"},
            ],
        )
        return self._get_response_content(response, "ResultsByTime")

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class ReservationUtilization(AWSSection):
    @property
    def name(self) -> str:
        return "reservation_utilization"

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400  # one day

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """Query the AWS GetReservationUtilization API.

        This API lags a day behind and we have to query the data starting the day
        before yesterday. So we query the last 2 data points and let the check
        report the most recent data point.
        In the AWS dashboard, we also only have data for from two days ago.
        """
        granularity_name, granularity_interval = "DAILY", self.granularity
        fmt = "%Y-%m-%d"

        params = {
            "TimePeriod": {
                "Start": datetime.strftime(NOW - 2 * timedelta(seconds=granularity_interval), fmt),
                "End": datetime.strftime(NOW, fmt),
            },
            "Granularity": granularity_name,
        }
        try:
            response = self._client.get_reservation_utilization(**params)  # type: ignore[attr-defined]
        # NOTE: The suppression below is needed because of BaseClientExceptions.__getattr__ magic.
        except self._client.exceptions.DataUnavailableException:  # type: ignore[misc]
            logging.warning("ReservationUtilization: No data available")
            return []
        return self._get_response_content(response, "UtilizationsByTime")

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--EC2-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___|___ \                            |
#   |                         |  _|| |     __) |                           |
#   |                         | |__| |___ / __/                            |
#   |                         |_____\____|_____|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class EC2Limits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "ec2_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        quota_list = list(self._iter_service_quotas("ec2"))
        quota_dicts = [q.model_dump() for q in quota_list]

        response = self._client.describe_instances()  # type: ignore[attr-defined]
        reservations = self._get_response_content(response, "Reservations")

        response = self._client.describe_reserved_instances()  # type: ignore[attr-defined]
        reserved_instances = self._get_response_content(response, "ReservedInstances")

        response = self._client.describe_addresses()  # type: ignore[attr-defined]
        addresses = self._get_response_content(response, "Addresses")

        response = self._client.describe_security_groups()  # type: ignore[attr-defined]
        security_groups = self._get_response_content(response, "SecurityGroups")

        response = self._client.describe_network_interfaces()  # type: ignore[attr-defined]
        interfaces = self._get_response_content(response, "NetworkInterfaces")

        response = self._client.describe_spot_instance_requests()  # type: ignore[attr-defined]
        spot_inst_requests = self._get_response_content(response, "SpotInstanceRequests")

        response = self._client.describe_spot_fleet_requests()  # type: ignore[attr-defined]
        spot_fleet_requests = self._get_response_content(response, "SpotFleetRequestConfigs")

        return (
            reservations,
            reserved_instances,
            addresses,
            security_groups,
            interfaces,
            spot_inst_requests,
            spot_fleet_requests,
            quota_dicts,
        )

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        (
            reservations,
            reserved_instances,
            addresses,
            security_groups,
            interfaces,
            spot_inst_requests,
            spot_fleet_requests,
            quotas,
        ) = raw_content.content
        instances = {inst["InstanceId"]: inst for res in reservations for inst in res["Instances"]}
        res_instances = {inst["ReservedInstancesId"]: inst for inst in reserved_instances}
        EC2InstFamiliesquotas = {
            q["QuotaName"]: q["Value"]
            for q in quotas
            if q["QuotaName"] in AWSEC2InstFamilies.values()
        }

        self._add_instance_limits(
            instances, res_instances, spot_inst_requests, EC2InstFamiliesquotas
        )
        self._add_addresses_limits(addresses)
        self._add_security_group_limits(security_groups)
        self._add_interface_limits(interfaces)
        self._add_spot_inst_limits(spot_inst_requests)
        self._add_spot_fleet_limits(spot_fleet_requests)
        return AWSComputedContent(reservations, raw_content.cache_timestamp)

    def _add_instance_limits(
        self,
        instances: Mapping[str, object],
        res_instances: Mapping[str, object],
        spot_inst_requests: Sequence[Mapping[str, object]],
        instance_quotas: Mapping[str, int],
    ) -> None:
        inst_limits = self._get_inst_limits(instances, spot_inst_requests)
        res_limits = self._get_res_inst_limits(res_instances)

        total_ris = 0
        running_ris = 0
        ondemand_limits: dict[str, int] = {}
        # subtract reservations from instance usage
        for inst_az, inst_types in inst_limits.items():
            if inst_az not in res_limits:
                for inst_type, count in inst_types.items():
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                continue

            # else we have reservations for this AZ
            for inst_type, count in inst_types.items():
                if inst_type not in res_limits[inst_az]:
                    # no reservations for this type
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                    continue

                amount_res_inst_type = res_limits[inst_az][inst_type]
                ondemand = count - amount_res_inst_type
                total_ris += amount_res_inst_type
                if count < amount_res_inst_type:
                    running_ris += count
                else:
                    running_ris += amount_res_inst_type
                if ondemand < 0:
                    # we have unused reservations
                    continue
                ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + ondemand

        dflt_ondemand_limit, _reserved_limit1, _spot_limit1 = AWSEC2LimitsDefault
        total_instances = 0
        for inst_type, count in ondemand_limits.items():
            ondemand_limit, _reserved_limit, _spot_limit = AWSEC2LimitsSpecial.get(
                inst_type, AWSEC2LimitsDefault
            )
            if inst_type.endswith("_vcpu"):
                # Maybe should raise instead of unknown family
                try:
                    inst_fam_name = AWSEC2InstFamilies[inst_type[0]].localize(lambda x: x)
                except KeyError:
                    inst_fam_name = "Unknown Instance Family"
                ondemand_limit = instance_quotas.get(inst_fam_name, ondemand_limit)
                self._add_limit(
                    "",
                    AWSLimit(
                        "running_ondemand_instances_%s" % inst_type.lower(),
                        inst_fam_name + " vCPUs",
                        ondemand_limit,
                        count,
                    ),
                )
                continue

            total_instances += count
            self._add_limit(
                "",
                AWSLimit(
                    "running_ondemand_instances_%s" % inst_type,
                    "Running On-Demand %s Instances" % inst_type,
                    ondemand_limit,
                    count,
                ),
            )
        self._add_limit(
            "",
            AWSLimit(
                "running_ondemand_instances_total",
                "Total Running On-Demand Instances",
                dflt_ondemand_limit,
                total_instances,
            ),
        )

    def _get_inst_limits(self, instances, spot_inst_requests):
        spot_instance_ids = [inst["InstanceId"] for inst in spot_inst_requests]
        inst_limits: dict[str, dict[str, int]] = {}
        for inst_id, inst in instances.items():
            if inst_id in spot_instance_ids:
                continue
            if inst["State"]["Name"] in ["stopped", "terminated"]:
                continue
            inst_type = inst["InstanceType"]
            inst_az = inst["Placement"]["AvailabilityZone"]
            inst_limits.setdefault(inst_az, {})[inst_type] = (
                inst_limits.get(inst_az, {}).get(inst_type, 0) + 1
            )

            vcount = inst["CpuOptions"]["CoreCount"] * inst["CpuOptions"]["ThreadsPerCore"]
            vcpu_family = "%s_vcpu" % (inst_type[0] if inst_type[0] in AWSEC2InstFamilies else "_")
            inst_limits[inst_az][vcpu_family] = inst_limits[inst_az].get(vcpu_family, 0) + vcount
        return inst_limits

    def _get_res_inst_limits(self, res_instances):
        res_limits: dict[str, dict[str, int]] = {}
        for res_inst in res_instances.values():
            if res_inst["State"] != "active":
                continue
            inst_type = res_inst["InstanceType"]
            if inst_type not in AWSEC2InstTypes:
                logging.info("%s: Unknown instance type '%s'", self.name, inst_type)
                continue

            inst_az = res_inst.get("AvailabilityZone")
            if not inst_az:
                logging.info("AvailabilityZone not available")
                continue
            res_limits.setdefault(inst_az, {})[inst_type] = (
                res_limits.get(inst_az, {}).get(inst_type, 0) + res_inst["InstanceCount"]
            )
        return res_limits

    def _add_addresses_limits(self, addresses: Sequence[Mapping[str, object]]) -> None:
        # Global limits
        vpc_addresses = 0
        std_addresses = 0
        for address in addresses:
            domain = address["Domain"]
            if domain == "vpc":
                vpc_addresses += 1
            elif domain == "standard":
                std_addresses += 1
        self._add_limit(
            "",
            AWSLimit(
                "vpc_elastic_ip_addresses",
                "VPC Elastic IP addresses",
                5,
                vpc_addresses,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "elastic_ip_addresses",
                "Elastic IP addresses",
                5,
                std_addresses,
            ),
        )

    def _add_security_group_limits(self, security_groups: Sequence[Mapping]) -> None:
        self._add_limit(
            "",
            AWSLimit(
                "vpc_sec_groups",
                "VPC security groups",
                2500,
                len(security_groups),
            ),
        )

        for sec_group in security_groups:
            vpc_id = sec_group["VpcId"]
            if not vpc_id:
                continue
            self._add_limit(
                "",
                AWSLimit(
                    "vpc_sec_group_rules",
                    "Rules of VPC security group %s" % sec_group["GroupName"],
                    120,
                    len(sec_group["IpPermissions"]),
                ),
            )

    def _add_interface_limits(self, interfaces: Sequence[Mapping]) -> None:
        # since there can also be interfaces which are not attached to an instance, we add these
        # limits to the host running the agent instead of to individual instances
        for iface in interfaces:
            self._add_limit(
                "",
                AWSLimit(
                    "if_vpc_sec_group",
                    "VPC security groups of elastic network interface %s"
                    % iface["NetworkInterfaceId"],
                    5,
                    len(iface["Groups"]),
                ),
            )

    def _add_spot_inst_limits(self, spot_inst_requests: Sequence[Mapping[str, object]]) -> None:
        count_spot_inst_reqs = 0
        for spot_inst_req in spot_inst_requests:
            if spot_inst_req["State"] in ["open", "active"]:
                count_spot_inst_reqs += 1
        self._add_limit(
            "",
            AWSLimit(
                "spot_inst_requests",
                "Spot Instance Requests",
                20,
                count_spot_inst_reqs,
            ),
        )

    def _add_spot_fleet_limits(self, spot_fleet_requests: Sequence[Mapping]) -> None:
        active_spot_fleet_requests = 0
        total_target_cap = 0
        for spot_fleet_req in spot_fleet_requests:
            if spot_fleet_req["SpotFleetRequestState"] != "active":
                continue

            active_spot_fleet_requests += 1
            total_target_cap += spot_fleet_req["SpotFleetRequestConfig"]["TargetCapacity"]

        self._add_limit(
            "",
            AWSLimit(
                "active_spot_fleet_requests",
                "Active Spot Fleet Requests",
                1000,
                active_spot_fleet_requests,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "spot_fleet_total_target_capacity",
                "Spot Fleet Requests Total Target Capacity",
                5000,
                total_target_cap,
            ),
        )


class EC2Summary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ec2_names"]
        self._tags = self._config.service_config["ec2_tags"]

    @property
    def name(self) -> str:
        return "ec2_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ec2_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]] | None:
        (colleague_contents,) = args
        if self._tags is None and self._names is not None:
            return self._fetch_instances_filtered_by_names(colleague_contents.content)
        if self._tags is not None:
            return self._fetch_instances_filtered_by_tags(colleague_contents.content)

        return self._fetch_instances_without_filter()

    def _fetch_instances_filtered_by_names(
        self, col_reservations: Sequence[dict]
    ) -> Sequence[Mapping[str, object]]:
        if col_reservations:
            instances = [
                inst
                for res in col_reservations
                for inst in res["Instances"]
                if inst["InstanceId"] in self._names
            ]
        else:
            response = self._client.describe_instances(InstanceIds=self._names)  # type: ignore[attr-defined]
            instances = [
                inst
                for res in self._get_response_content(response, "Reservations")
                for inst in res["Instances"]
            ]
        return instances

    def _fetch_instances_filtered_by_tags(
        self, col_reservations: list
    ) -> list[Mapping[str, object]] | None:
        if col_reservations:
            tags = self.prepare_tags_for_api_response(self._tags)
            return (
                [
                    inst
                    for res in col_reservations
                    for inst in res["Instances"]
                    for tag in inst.get("Tags", [])
                    if tag in tags
                ]
                if tags
                else None
            )

        instances = []
        for chunk in _chunks(self._tags, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_instances(Filters=chunk)  # type: ignore[attr-defined]
            instances.extend(
                [
                    inst
                    for res in self._get_response_content(response, "Reservations")
                    for inst in res["Instances"]
                ]
            )
        return instances

    def _fetch_instances_without_filter(self) -> Sequence[Mapping[str, object]]:
        response = self._client.describe_instances()  # type: ignore[attr-defined]
        return [
            inst
            for res in self._get_response_content(response, "Reservations")
            for inst in res["Instances"]
        ]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            self._format_instances(raw_content.content), raw_content.cache_timestamp
        )

    def _format_instances(self, instances):
        formatted_instances = {}
        for inst in instances:
            inst_id = _get_ec2_piggyback_hostname(
                self._config.piggyback_naming_convention, inst, self._region
            )
            if inst_id:
                inst["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(inst.get("Tags", []))
                formatted_instances[inst_id] = inst
        return formatted_instances

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class EC2Labels(AWSSectionLabels):
    @property
    def name(self) -> str:
        return "ec2_labels"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, str]] | None:
        (colleague_contents,) = args
        return colleague_contents.content

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            {
                ec2_instance_id: inst.get("TagsForCmkLabels", [])
                for ec2_instance_id, inst in raw_content.content.items()
                if inst.get("TagsForCmkLabels")
            },
            raw_content.cache_timestamp,
        )


class EC2SecurityGroups(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ec2_names"]
        self._tags = self._config.service_config["ec2_tags"]

    @property
    def name(self) -> str:
        return "ec2_security_groups"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        sec_groups = self._describe_security_groups()
        return {group["GroupId"]: group for group in sec_groups}

    def _describe_security_groups(self):
        if self._names is not None:
            response = self._client.describe_security_groups(InstanceIds=self._names)  # type: ignore[attr-defined]
            return self._get_response_content(response, "SecurityGroups")

        if self._tags is not None:
            sec_groups = []
            for chunk in _chunks(self._tags, length=200):
                # EC2 FilterLimitExceeded: The maximum number of filter values
                # specified on a single call is 200
                response = self._client.describe_security_groups(Filters=chunk)  # type: ignore[attr-defined]
                sec_groups.extend(self._get_response_content(response, "SecurityGroups"))
            return sec_groups

        response = self._client.describe_security_groups()  # type: ignore[attr-defined]
        return self._get_response_content(response, "SecurityGroups")

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for instance_name, instance in colleague_contents.content.items():
            for security_group_from_instance in instance.get("SecurityGroups", []):
                security_group = raw_content.content.get(security_group_from_instance["GroupId"])
                if security_group is None:
                    continue
                content_by_piggyback_hosts.setdefault(instance_name, []).append(security_group)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class EC2(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "ec2"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    @property
    def host_labels(self) -> Mapping[str, str]:
        return {"cmk/aws/ec2": "instance"}

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, (instance_name, instance) in enumerate(colleague_contents.content.items()):
            instance_id = instance["InstanceId"]
            for metric_name, unit in [
                ("CPUCreditUsage", "Count"),
                ("CPUCreditBalance", "Count"),
                ("CPUUtilization", "Percent"),
                ("DiskReadOps", "Count"),
                ("DiskWriteOps", "Count"),
                ("DiskReadBytes", "Bytes"),
                ("DiskWriteBytes", "Bytes"),
                ("NetworkIn", "Bytes"),
                ("NetworkOut", "Bytes"),
                ("StatusCheckFailed_Instance", "Count"),
                ("StatusCheckFailed_System", "Count"),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": instance_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/EC2",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {
                                        "Name": "InstanceId",
                                        "Value": instance_id,
                                    }
                                ],
                            },
                            "Period": self.period,
                            "Stat": "Average",
                            "Unit": unit,
                        },
                    }
                )
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows, self.host_labels)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


# .
#   .--EBS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____| __ ) ___|                            |
#   |                         |  _| |  _ \___ \                            |
#   |                         | |___| |_) |__) |                           |
#   |                         |_____|____/____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# EBS are attached to EC2 instances. Thus we put the content to related EC2
# instance as piggyback host.


class EBSLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "ebs_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        response = self._client.describe_volumes()  # type: ignore[attr-defined]
        volumes = self._get_response_content(response, "Volumes")

        response = self._client.describe_snapshots(OwnerIds=["self"])  # type: ignore[attr-defined]
        snapshots = self._get_response_content(response, "Snapshots")
        return volumes, snapshots

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        volumes, snapshots = raw_content.content

        vol_storage_standard = 0
        vol_storage_io1 = 0
        vol_storage_io2 = 0
        vol_storage_gp2 = 0
        vol_storage_gp3 = 0
        vol_storage_sc1 = 0
        vol_storage_st1 = 0
        vol_iops_io1 = 0
        vol_iops_io2 = 0
        for volume in volumes:
            vol_type = volume["VolumeType"]
            vol_size = volume["Size"]
            if vol_type == "standard":
                vol_storage_standard += vol_size
            elif vol_type == "io1":
                vol_storage_io1 += vol_size
                vol_iops_io1 += volume["Iops"]
            elif vol_type == "io2":
                vol_storage_io2 += vol_size
                vol_iops_io2 += volume["Iops"]
            elif vol_type == "gp2":
                vol_storage_gp2 += vol_size
            elif vol_type == "gp3":
                vol_storage_gp3 += vol_size
            elif vol_type == "sc1":
                vol_storage_sc1 += vol_size
            elif vol_type == "st1":
                vol_storage_st1 += vol_size
            else:
                logging.info("%s: Unhandled volume type: '%s'", self.name, vol_type)

        # These are total limits and not instance specific
        # Space values are in TiB.
        # Reference: https://docs.aws.amazon.com/general/latest/gr/ebs-service.html
        self._add_limit(
            "",
            AWSLimit(
                "block_store_snapshots",
                "Block store snapshots",
                100000,
                len(snapshots),
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_standard",
                "Magnetic volumes space",
                300,
                vol_storage_standard,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_io1",
                "Provisioned IOPS SSD (io1) space",
                300,
                vol_storage_io1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_iops_io1",
                "Provisioned IOPS SSD (io1) IO operations per second",
                300000,
                vol_storage_io1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_io2",
                "Provisioned IOPS SSD (io2) space",
                20,
                vol_storage_io2,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_iops_io2",
                "Provisioned IOPS SSD (io2) IO operations per second",
                100000,
                vol_storage_io2,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_gp2",
                "General Purpose SSD (gp2) space",
                300,
                vol_storage_gp2,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_gp3",
                "General Purpose SSD (gp3) space",
                300,
                vol_storage_gp3,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_sc1",
                "Cold HDD space",
                300,
                vol_storage_sc1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_st1",
                "Throughput Optimized HDD space",
                300,
                vol_storage_st1,
            ),
        )
        return AWSComputedContent(volumes, raw_content.cache_timestamp)


class EBSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ebs_names"]
        self._tags = self._config.service_config["ebs_tags"]

    @property
    def name(self) -> str:
        return "ebs_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ebs_limits")
        volumes = []
        max_cache_timestamp = 0.0
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            volumes = colleague.content

        colleague = self._received_results.get("ec2_summary")
        instances = {}
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            instances = colleague.content

        return AWSColleagueContents((volumes, instances), max_cache_timestamp)

    def get_live_data(self, *args: AWSColleagueContents) -> Mapping[str, Mapping[str, object]]:
        (colleague_contents,) = args
        col_volumes, _col_instances = colleague_contents.content
        if self._tags is None and self._names is not None:
            volumes = self._fetch_volumes_filtered_by_names(col_volumes)
        elif self._tags is not None:
            volumes = self._fetch_volumes_filtered_by_tags(col_volumes)
        else:
            volumes = self._fetch_volumes_without_filter(col_volumes)

        formatted_volumes = {v["VolumeId"]: v for v in volumes}
        for vol_id, vol in formatted_volumes.items():
            response = self._client.describe_volume_status(VolumeIds=[vol_id])  # type: ignore[attr-defined]
            for state in self._get_response_content(response, "VolumeStatuses"):
                if state["VolumeId"] == vol_id:
                    vol.setdefault("VolumeStatus", state["VolumeStatus"])
        return formatted_volumes

    def _fetch_volumes_filtered_by_names(self, col_volumes):
        if col_volumes:
            return [v for v in col_volumes if v["VolumeId"] in self._names]
        response = self._client.describe_volumes(VolumeIds=self._names)  # type: ignore[attr-defined]
        return self._get_response_content(response, "Volumes")

    def _fetch_volumes_filtered_by_tags(self, col_volumes):
        if col_volumes:
            tags = self.prepare_tags_for_api_response(self._tags)
            if tags:
                return [v for v in col_volumes for tag in v.get("Tags", []) if tag in tags]

        volumes = []
        for chunk in _chunks(self._tags, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_volumes(Filters=chunk)  # type: ignore[attr-defined]
            volumes.extend(self._get_response_content(response, "Volumes"))
        return volumes

    def _fetch_volumes_without_filter(self, col_volumes):
        if col_volumes:
            return col_volumes
        response = self._client.describe_volumes()  # type: ignore[attr-defined]
        return self._get_response_content(response, "Volumes")

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        _col_volumes, col_instances = colleague_contents.content
        instance_name_mapping = {v["InstanceId"]: k for k, v in col_instances.items()}

        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for vol in raw_content.content.values():
            vol["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(vol.get("Tags", []))

            instance_names = []
            for attachment in vol["Attachments"]:
                # Just for security
                if vol["VolumeId"] != attachment["VolumeId"]:
                    continue
                instance_name = instance_name_mapping.get(attachment["InstanceId"])
                if instance_name is None:
                    instance_name = ""
                instance_names.append(instance_name)

            # Should be attached to max. one instance
            for instance_name in instance_names:
                content_by_piggyback_hosts.setdefault(instance_name, [])
                content_by_piggyback_hosts[instance_name].append(vol)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class EBS(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "ebs"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ebs_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(
                [
                    (instance_name, row["VolumeId"], row["VolumeType"])
                    for instance_name, rows in colleague.content.items()
                    for row in rows
                ],
                colleague.cache_timestamp,
            )
        return AWSColleagueContents([], 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        muv: list[tuple[str, str, list[str]]] = [
            ("VolumeReadOps", "Count", []),
            ("VolumeWriteOps", "Count", []),
            ("VolumeReadBytes", "Bytes", []),
            ("VolumeWriteBytes", "Bytes", []),
            ("VolumeQueueLength", "Count", []),
            ("BurstBalance", "Percent", ["gp2", "st1", "sc1"]),
            # ("VolumeThroughputPercentage", "Percent", ["io1"]),
            # ("VolumeConsumedReadWriteOps", "Count", ["io1"]),
            # ("VolumeTotalReadTime", "Seconds", []),
            # ("VolumeTotalWriteTime", "Seconds", []),
            # ("VolumeIdleTime", "Seconds", []),
            # ("VolumeStatus", None, []),
            # ("IOPerformance", None, ["io1"]),
        ]
        metrics: Metrics = []
        for idx, (instance_name, volume_name, volume_type) in enumerate(colleague_contents.content):
            for metric_name, unit, volume_types in muv:
                if volume_types and volume_type not in volume_types:
                    continue
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": instance_name,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/EBS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "VolumeID",
                                    "Value": volume_name,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": "Average",
                    },
                }
                if unit:
                    metric["MetricStat"]["Unit"] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


# .
#   .--S3------------------------------------------------------------------.
#   |                             ____ _____                               |
#   |                            / ___|___ /                               |
#   |                            \___ \ |_ \                               |
#   |                             ___) |__) |                              |
#   |                            |____/____/                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class S3BucketHelper:
    """
    Helper Class for S3
    """

    @staticmethod
    def list_buckets(client: BaseClient) -> Buckets:
        """
        Get all buckets with LocationConstraint
        """
        bucket_list = client.list_buckets()  # type: ignore[attr-defined]
        for bucket in bucket_list["Buckets"]:
            bucket_name = bucket["Name"]

            # request additional LocationConstraint information
            try:
                response = client.get_bucket_location(Bucket=bucket_name)  # type: ignore[attr-defined]
            except client.exceptions.ClientError as e:
                # An error occurred (AccessDenied) when calling the GetBucketLocation operation:
                # Access Denied
                logging.info("S3BucketHelper/%s: Access denied, %s", bucket_name, e)
                continue

            if response:
                if response["LocationConstraint"] is None:
                    location_constraint = "us-east-1"  # for this region, LocationConstraint is None
                else:
                    location_constraint = response["LocationConstraint"]
                bucket["LocationConstraint"] = location_constraint
        return bucket_list["Buckets"] if bucket_list else []


class S3Limits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "s3_limits"

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)

        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Buckets:
        """
        There's no API method for getting account limits thus we have to
        fetch all buckets.
        """
        bucket_list = S3BucketHelper.list_buckets(self._client)
        return bucket_list

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        self._add_limit(
            "", AWSLimit("buckets", "Buckets", 100, len(raw_content.content)), region="Global"
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class S3Summary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["s3_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["s3_tags"])

    @property
    def name(self) -> str:
        return "s3_summary"

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("s3_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        found_buckets = []
        for bucket in self._list_buckets(colleague_contents):
            bucket_name = bucket["Name"]

            try:
                response = self._client.get_bucket_tagging(Bucket=bucket_name)  # type: ignore[attr-defined]
            except self._client.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.info("%s/%s: No tags set, %s", self.name, bucket_name, e)
                response = {}

            tagging = self._get_response_content(response, "TagSet")
            if self._matches_tag_conditions(tagging):
                bucket["Tagging"] = tagging  # Legacy tags, to be removed when check is adapted
                bucket["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tagging)
                found_buckets.append(bucket)
        return found_buckets

    def _list_buckets(
        self, colleague_contents: AWSColleagueContents
    ) -> Sequence[dict[str, object]]:
        # use previous fetched data or fetch it now
        if colleague_contents.content:
            bucket_list = colleague_contents.content
        else:
            # filter buckets by region
            bucket_list = S3BucketHelper.list_buckets(self._client)

        # filter buckets by region
        bucket_list = [
            bucket
            for bucket in bucket_list
            if "LocationConstraint" in bucket and bucket["LocationConstraint"] == self.region
        ]

        # filter buckets by name if there is a filter
        if self._names is not None:
            return [bucket for bucket in bucket_list if bucket["Name"] in self._names]

        return bucket_list

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            {bucket["Name"]: bucket for bucket in raw_content.content}, raw_content.cache_timestamp
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class S3(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "s3"

    @property
    def cache_interval(self) -> int:
        # BucketSizeBytes and NumberOfObjects are available per day
        # and must include 00:00h
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("s3_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content):
            for metric_name, unit, storage_classes in [
                (
                    "BucketSizeBytes",
                    "Bytes",
                    [
                        "StandardStorage",
                        "StandardIAStorage",
                        "ReducedRedundancyStorage",
                    ],
                ),
                ("NumberOfObjects", "Count", ["AllStorageTypes"]),
            ]:
                for storage_class in storage_classes:
                    metrics.append(
                        {
                            "Id": self._create_id_for_metric_data_query(
                                idx, metric_name, storage_class
                            ),
                            "Label": bucket_name,
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/S3",
                                    "MetricName": metric_name,
                                    "Dimensions": [
                                        {
                                            "Name": "BucketName",
                                            "Value": bucket_name,
                                        },
                                        {
                                            "Name": "StorageType",
                                            "Value": storage_class,
                                        },
                                    ],
                                },
                                "Period": self.period,
                                "Stat": "Average",
                                "Unit": unit,
                            },
                        }
                    )
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row["Label"])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class S3Requests(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "s3_requests"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("s3_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content):
            for metric_name, unit, stat in [
                ("AllRequests", "Count", "Sum"),
                ("GetRequests", "Count", "Sum"),
                ("PutRequests", "Count", "Sum"),
                ("DeleteRequests", "Count", "Sum"),
                ("HeadRequests", "Count", "Sum"),
                ("PostRequests", "Count", "Sum"),
                ("SelectRequests", "Count", "Sum"),
                # The following two metrics seem to have the wrong name in the documentation
                # https://docs.aws.amazon.com/AmazonS3/latest/dev/cloudwatch-monitoring.html
                ("SelectBytesScanned", "Bytes", "Sum"),
                ("SelectBytesReturned", "Bytes", "Sum"),
                ("ListRequests", "Count", "Sum"),
                ("BytesDownloaded", "Bytes", "Sum"),
                ("BytesUploaded", "Bytes", "Sum"),
                ("4xxErrors", "Count", "Sum"),
                ("5xxErrors", "Count", "Sum"),
                ("FirstByteLatency", "Milliseconds", "Average"),
                ("TotalRequestLatency", "Milliseconds", "Average"),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": bucket_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/S3",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {"Name": "BucketName", "Value": bucket_name},
                                    {"Name": "FilterId", "Value": "EntireBucket"},
                                ],
                            },
                            "Period": self.period,
                            "Stat": stat,
                            "Unit": unit,
                        },
                    }
                )
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row["Label"])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--Glacier-------------------------------------------------------------.
#   |                    ____ _            _                               |
#   |                   / ___| | __ _  ___(_) ___ _ __                     |
#   |                  | |  _| |/ _` |/ __| |/ _ \ '__|                    |
#   |                  | |_| | | (_| | (__| |  __/ |                       |
#   |                   \____|_|\__,_|\___|_|\___|_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class GlacierLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "glacier_limits"

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        There's no API method for getting account limits thus we have to
        fetch all vaults.
        """
        response = self._client.list_vaults()  # type: ignore[attr-defined]
        return self._get_response_content(response, "VaultList")

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        self._add_limit(
            "",
            AWSLimit(
                "number_of_vaults",
                "Vaults",
                1000,
                len(raw_content.content),
            ),
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class Glacier(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["glacier_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["glacier_tags"])

    @property
    def name(self) -> str:
        return "glacier"

    @property
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self) -> int:
        return 86400

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("glacier_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        """
        1. get all vaults from AWS Glacier.
        2. filter vaults by their name.
        3. get tags for the filtered vaults
        :param colleague_contents:
        :return: filtered list of vaults with their tags
        """
        (colleague_contents,) = args
        found_vaults = []
        for vault in self._filter_vaults_by_names(self._list_vaults(colleague_contents)):
            vault_name = vault["VaultName"]

            try:
                response = self._client.list_tags_for_vault(vaultName=vault_name)  # type: ignore[attr-defined]
            except botocore.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.warning("%s/%s: Exception, %s", self.name, vault_name, e)
                response = {}

            tags = self._get_response_content(response, "Tags")
            tag_list: Tags = [{"Key": key, "Value": value} for key, value in tags.items()]
            if self._matches_tag_conditions(tag_list):
                vault["Tagging"] = tags  # Legacy tags, to be removed when check is adapted
                vault["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tag_list)
                found_vaults.append(vault)

        return found_vaults

    def _filter_vaults_by_names(self, vault_list):
        """
        filter vaults by their VaultName
        :param vault_list: list of all vaults
        :return: filtered list of dicts
        """
        if not self._names:
            return vault_list

        return [vault for vault in vault_list if vault["VaultName"] in self._names]

    def _list_vaults(self, colleague_contents: AWSColleagueContents) -> Mapping[str, str | int]:
        """
        get list of vaults from previous call or get it now
        :param colleague_contents:
        :return:
        """
        if colleague_contents and colleague_contents.content:
            return colleague_contents.content
        return self._get_response_content(self._client.list_vaults(), "VaultList")  # type: ignore[attr-defined]

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True

        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--ELB-----------------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "elb_limits"

    @property
    def cache_interval(self) -> int:
        # If you change this, you might have to adjust the defaults for 'levels_spillover' in checks/aws_elb
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        The AWS/ELB API method 'describe_account_limits' provides limit values
        but no values about the usage per limit thus we have to gather the usage
        values from 'describe_load_balancers'.
        """
        load_balancers = [
            load_balancer
            for page in self._client.get_paginator("describe_load_balancers").paginate()
            for load_balancer in self._get_response_content(page, "LoadBalancerDescriptions")
        ]

        response = self._client.describe_account_limits()  # type: ignore[attr-defined]
        limits = self._get_response_content(response, "Limits")
        return load_balancers, limits

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        load_balancers, limits = raw_content.content
        limits = {r["Name"]: int(r["Max"]) for r in limits}

        self._add_limit(
            "",
            AWSLimit(
                "load_balancers",
                "Load balancers",
                limits["classic-load-balancers"],
                len(load_balancers),
            ),
        )

        for load_balancer in load_balancers:
            dns_name = load_balancer["DNSName"]
            self._add_limit(
                dns_name,
                AWSLimit(
                    "load_balancer_listeners",
                    "Listeners",
                    limits["classic-listeners"],
                    len(load_balancer["ListenerDescriptions"]),
                ),
            )
            self._add_limit(
                dns_name,
                AWSLimit(
                    "load_balancer_registered_instances",
                    "Registered instances",
                    limits["classic-registered-instances"],
                    len(load_balancer["Instances"]),
                ),
            )
        return AWSComputedContent(load_balancers, raw_content.cache_timestamp)


class ELBSummaryGeneric(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
        resource: str = "",
    ) -> None:
        self._resource = resource
        if self._resource == "elb":
            self._describe_load_balancers_karg = "LoadBalancerNames"
            self._describe_load_balancers_key = "LoadBalancerDescriptions"
        elif self._resource == "elbv2":
            self._describe_load_balancers_karg = "Names"
            self._describe_load_balancers_key = "LoadBalancers"
        else:
            raise AssertionError(
                "ELBSummaryGeneric: resource argument must be either 'elb' or 'elbv2'"
            )

        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["%s_names" % resource]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["%s_tags" % resource]
        )

    @property
    def name(self) -> str:
        return "%s_summary" % self._resource

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("%s_limits" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        found_load_balancers = []
        for load_balancer in self._describe_load_balancers(colleague_contents):
            response = self._get_load_balancer_tags(load_balancer)
            tagging = [
                tag
                for tag_descr in self._get_response_content(response, "TagDescriptions")
                for tag in tag_descr["Tags"]
            ]
            if self._matches_tag_conditions(tagging):
                load_balancer["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tagging)
                found_load_balancers.append(load_balancer)
        return found_load_balancers

    def _get_load_balancer_tags(self, load_balancer):
        if self._resource == "elb":
            return self._client.describe_tags(LoadBalancerNames=[load_balancer["LoadBalancerName"]])  # type: ignore[attr-defined]
        return self._client.describe_tags(ResourceArns=[load_balancer["LoadBalancerArn"]])  # type: ignore[attr-defined]

    def _describe_load_balancers(
        self, colleague_contents: AWSColleagueContents
    ) -> Sequence[dict[str, object]]:
        if self._names is not None:
            if colleague_contents.content:
                return [
                    load_balancer
                    for load_balancer in colleague_contents.content
                    if load_balancer["LoadBalancerName"] in self._names
                ]
            page_iterator = self._client.get_paginator("describe_load_balancers").paginate(
                **{self._describe_load_balancers_karg: self._names}
            )

        else:
            if colleague_contents.content:
                return colleague_contents.content
            page_iterator = self._client.get_paginator("describe_load_balancers").paginate()

        return [
            load_balancer
            for page in page_iterator
            for load_balancer in self._get_response_content(page, self._describe_load_balancers_key)
        ]

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, str] = {}
        for load_balancer in raw_content.content:
            if (dns_name := load_balancer.get("DNSName")) is None:
                # SUP-15023
                # We skip "gateway" type load balancers
                # because they don't provide DNSName information
                continue
            content_by_piggyback_hosts.setdefault(dns_name, load_balancer)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class ELBLabelsGeneric(AWSSectionLabels):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
        resource: str = "",
    ) -> None:
        self._resource = resource
        super().__init__(client, region, config, distributor=distributor)

    @property
    def name(self) -> str:
        return "%s_generic_labels" % self._resource

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("%s_summary" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> object:
        (colleague_contents,) = args
        return colleague_contents.content

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        computed_content = {
            elb_instance_id: data.get("TagsForCmkLabels")
            for elb_instance_id, data in raw_content.content.items()
            if data.get("TagsForCmkLabels")
        }
        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class ELBHealth(AWSSection):
    @property
    def name(self) -> str:
        return "elb_health"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Mapping[str, Sequence[str]]:
        (colleague_contents,) = args
        load_balancers: dict[str, list[str]] = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.items():
            load_balancer_name = load_balancer["LoadBalancerName"]
            response = self._client.describe_instance_health(LoadBalancerName=load_balancer_name)  # type: ignore[attr-defined]
            states = self._get_response_content(response, "InstanceStates")
            if states:
                load_balancers.setdefault(load_balancer_dns_name, states)
        return load_balancers

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.items()
        ]


class ELB(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "elb"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    @property
    def host_labels(self) -> Mapping[str, str]:
        return {"cmk/aws/service": "elb"}

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, (load_balancer_dns_name, load_balancer) in enumerate(
            colleague_contents.content.items()
        ):
            load_balancer_name = load_balancer["LoadBalancerName"]
            for metric_name, stat in [
                ("RequestCount", "Sum"),
                ("SurgeQueueLength", "Maximum"),
                ("SpilloverCount", "Sum"),
                ("Latency", "Average"),
                ("HTTPCode_ELB_4XX", "Sum"),
                ("HTTPCode_ELB_5XX", "Sum"),
                ("HTTPCode_Backend_2XX", "Sum"),
                ("HTTPCode_Backend_3XX", "Sum"),
                ("HTTPCode_Backend_4XX", "Sum"),
                ("HTTPCode_Backend_5XX", "Sum"),
                ("HealthyHostCount", "Average"),
                ("UnHealthyHostCount", "Average"),
                ("BackendConnectionErrors", "Sum"),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": load_balancer_dns_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ELB",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {
                                        "Name": "LoadBalancerName",
                                        "Value": load_balancer_name,
                                    }
                                ],
                            },
                            "Period": self.period,
                            "Stat": stat,
                        },
                    }
                )
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows, self.host_labels)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


# .
#   .--ELBv2---------------------------------------------------------------.
#   |                    _____ _     ____       ____                       |
#   |                   | ____| |   | __ )_   _|___ \                      |
#   |                   |  _| | |   |  _ \ \ / / __) |                     |
#   |                   | |___| |___| |_) \ V / / __/                      |
#   |                   |_____|_____|____/ \_/ |_____|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBv2Limits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "elbv2_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        The AWS/ELBv2 API method 'describe_account_limits' provides limit values
        but no values about the usage per limit thus we have to gather the usage
        values from 'describe_load_balancers'.
        """
        load_balancers = [
            load_balancer
            for page in self._client.get_paginator("describe_load_balancers").paginate()
            for load_balancer in self._get_response_content(page, "LoadBalancers")
        ]

        for load_balancer in load_balancers:
            lb_arn = load_balancer["LoadBalancerArn"]

            response = self._client.describe_target_groups(LoadBalancerArn=lb_arn)  # type: ignore[attr-defined]
            load_balancer["TargetGroups"] = self._get_response_content(response, "TargetGroups")

            response = self._client.describe_listeners(LoadBalancerArn=lb_arn)  # type: ignore[attr-defined]
            listeners = self._get_response_content(response, "Listeners")
            load_balancer["Listeners"] = listeners

            if load_balancer["Type"] == "application":
                rules = []
                for listener in listeners:
                    response = self._client.describe_rules(ListenerArn=listener["ListenerArn"])  # type: ignore[attr-defined]
                    rules.extend(self._get_response_content(response, "Rules"))

                # Limit 100 holds for rules which are not default, see AWS docs:
                # https://docs.aws.amazon.com/de_de/general/latest/gr/aws_service_limits.html
                # > Limits für Elastic Load Balancing
                load_balancer["Rules"] = [rule for rule in rules if not rule["IsDefault"]]

        response = self._client.describe_account_limits()  # type: ignore[attr-defined]
        limits = self._get_response_content(response, "Limits")
        return load_balancers, limits

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        load_balancers, limits = raw_content.content
        limits = {r["Name"]: int(r["Max"]) for r in limits}

        alb_count = 0
        nlb_count = 0
        target_groups_count = 0
        for load_balancer in load_balancers:
            lb_dns_name = load_balancer["DNSName"]
            lb_type = load_balancer["Type"]

            lb_listeners_count = len(load_balancer.get("Listeners", []))
            lb_target_groups_count = len(load_balancer.get("TargetGroups", []))
            target_groups_count += lb_target_groups_count

            if lb_type == "application":
                alb_count += 1
                key = "application"
                title = "Application"
                self._add_limit(
                    lb_dns_name,
                    AWSLimit(
                        "application_load_balancer_rules",
                        "Application Load Balancer Rules",
                        limits["rules-per-application-load-balancer"],
                        len(load_balancer.get("Rules", [])),
                    ),
                )

                self._add_limit(
                    lb_dns_name,
                    AWSLimit(
                        "application_load_balancer_certificates",
                        "Application Load Balancer Certificates",
                        25,
                        len(
                            [
                                cert
                                for cert in load_balancer.get("Certificates", [])
                                if not cert["IsDefault"]
                            ]
                        ),
                    ),
                )

            elif lb_type == "network":
                nlb_count += 1
                key = "network"
                title = "Network"

            else:
                continue

            self._add_limit(
                lb_dns_name,
                AWSLimit(
                    "%s_load_balancer_listeners" % key,
                    "%s Load Balancer Listeners" % title,
                    limits["listeners-per-%s-load-balancer" % key],
                    lb_listeners_count,
                ),
            )

            self._add_limit(
                lb_dns_name,
                AWSLimit(
                    "%s_load_balancer_target_groups" % key,
                    "%s Load Balancer Target Groups" % title,
                    limits["targets-per-%s-load-balancer" % key],
                    lb_target_groups_count,
                ),
            )

        self._add_limit(
            "",
            AWSLimit(
                "application_load_balancers",
                "Application Load balancers",
                limits["application-load-balancers"],
                alb_count,
            ),
        )

        self._add_limit(
            "",
            AWSLimit(
                "network_load_balancers",
                "Network Load balancers",
                limits["network-load-balancers"],
                nlb_count,
            ),
        )

        self._add_limit(
            "",
            AWSLimit(
                "load_balancer_target_groups",
                "Load balancers target groups",
                limits["target-groups"],
                target_groups_count,
            ),
        )
        return AWSComputedContent(load_balancers, raw_content.cache_timestamp)


class ELBv2TargetGroups(AWSSection):
    @property
    def name(self) -> str:
        return "elbv2_target_groups"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> LoadBalancers:
        (colleague_contents,) = args
        load_balancers: LoadBalancers = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.items():
            load_balancer_type = load_balancer.get("Type")
            if load_balancer_type not in ["application", "network"]:
                # Just to be sure, that we do not describe target groups of other lbs
                continue

            if "TargetGroups" not in load_balancer:
                response = self._client.describe_target_groups(  # type: ignore[attr-defined]
                    LoadBalancerArn=load_balancer["LoadBalancerArn"]
                )
                load_balancer["TargetGroups"] = self._get_response_content(response, "TargetGroups")

            target_groups = load_balancer.get("TargetGroups", [])
            for target_group in target_groups:
                response = self._client.describe_target_health(  # type: ignore[attr-defined]
                    TargetGroupArn=target_group["TargetGroupArn"]
                )
                target_group_health_descrs = self._get_response_content(
                    response, "TargetHealthDescriptions"
                )
                target_group["TargetHealthDescriptions"] = target_group_health_descrs

            load_balancers.setdefault(load_balancer_dns_name, []).append(
                (load_balancer_type, target_groups)
            )
        return load_balancers

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.items()
        ]


# .
#   .--Application ELB-----------------------------------------------------.
#   |            _                _ _           _   _                      |
#   |           / \   _ __  _ __ | (_) ___ __ _| |_(_) ___  _ __           |
#   |          / _ \ | '_ \| '_ \| | |/ __/ _` | __| |/ _ \| '_ \          |
#   |         / ___ \| |_) | |_) | | | (_| (_| | |_| | (_) | | | |         |
#   |        /_/   \_\ .__/| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|         |
#   |                |_|   |_|                                             |
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBv2Application(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "elbv2_application"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, (load_balancer_dns_name, load_balancer) in enumerate(
            colleague_contents.content.items()
        ):
            load_balancer_dim = _elbv2_load_balancer_arn_to_dim(load_balancer["LoadBalancerArn"])
            for metric_name, stat in [
                ("ActiveConnectionCount", "Sum"),
                ("ClientTLSNegotiationErrorCount", "Sum"),
                ("ConsumedLCUs", "Average"),
                ("HTTP_Fixed_Response_Count", "Sum"),
                ("HTTP_Redirect_Count", "Sum"),
                ("HTTP_Redirect_Url_Limit_Exceeded_Count", "Sum"),
                ("HTTPCode_ELB_3XX_Count", "Sum"),
                ("HTTPCode_ELB_4XX_Count", "Sum"),
                ("HTTPCode_ELB_5XX_Count", "Sum"),
                ("HTTPCode_ELB_500_Count", "Sum"),
                ("HTTPCode_ELB_502_Count", "Sum"),
                ("HTTPCode_ELB_503_Count", "Sum"),
                ("HTTPCode_ELB_504_Count", "Sum"),
                ("IPv6ProcessedBytes", "Sum"),
                ("IPv6RequestCount", "Sum"),
                ("NewConnectionCount", "Sum"),
                ("ProcessedBytes", "Sum"),
                ("RejectedConnectionCount", "Sum"),
                ("RequestCount", "Sum"),
                ("RuleEvaluations", "Sum"),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": load_balancer_dns_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {
                                        "Name": "LoadBalancer",
                                        "Value": load_balancer_dim,
                                    }
                                ],
                            },
                            "Period": self.period,
                            "Stat": stat,
                        },
                    }
                )
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class ELBv2ApplicationTargetGroupsResponses(AWSSectionCloudwatch):
    """
    Additional monitoring for target groups of application load balancers.
    """

    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._separator = " "

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics_with_specs(
        self,
        colleague_contents: AWSColleagueContents,
        target_types: Sequence[str],
        metrics_to_get: Sequence[str],
    ) -> Metrics:
        metrics: Metrics = []

        for idx, (load_balancer_dns_name, load_balancer) in enumerate(
            colleague_contents.content.items()
        ):
            # these metrics only apply to application load balancers
            load_balancer_type = load_balancer.get("Type")
            if load_balancer_type != "application":
                continue

            load_balancer_dim = _elbv2_load_balancer_arn_to_dim(load_balancer["LoadBalancerArn"])

            for target_group in load_balancer["TargetGroups"]:
                # only add metrics if the target group is of the right type, for example, we do not
                # want to discover the service aws_elbv2_target_groups_http for target groups of
                # type 'lambda' or the service aws_elbv2_target_groups_lambda for target groups of
                # type 'instance'
                if target_group["TargetType"] not in target_types:
                    continue

                target_group_dim = _elbv2_target_group_arn_to_dim(target_group["TargetGroupArn"])

                for metric_name in metrics_to_get:
                    metrics.append(
                        {
                            "Id": self._create_id_for_metric_data_query(
                                idx,
                                metric_name,
                                target_group["TargetGroupName"].lower().replace("-", "_"),
                            ),
                            "Label": load_balancer_dns_name
                            + self._separator
                            + target_group["TargetGroupName"],
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/ApplicationELB",
                                    "MetricName": metric_name,
                                    "Dimensions": [
                                        {
                                            "Name": "LoadBalancer",
                                            "Value": load_balancer_dim,
                                        },
                                        {"Name": "TargetGroup", "Value": target_group_dim},
                                    ],
                                },
                                "Period": self.period,
                                "Stat": "Sum",
                            },
                        }
                    )

        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[object]] = {}
        for row in raw_content.content:
            load_bal_dns, target_group_name = row["Label"].split(self._separator)
            row["Label"] = target_group_name
            content_by_piggyback_hosts.setdefault(load_bal_dns, []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class ELBv2ApplicationTargetGroupsHTTP(ELBv2ApplicationTargetGroupsResponses):
    @property
    def name(self) -> str:
        return "elbv2_application_target_groups_http"

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        return self._get_metrics_with_specs(
            colleague_contents,
            ["instance", "ip"],
            [
                "RequestCount",
                "HTTPCode_Target_2XX_Count",
                "HTTPCode_Target_3XX_Count",
                "HTTPCode_Target_4XX_Count",
                "HTTPCode_Target_5XX_Count",
            ],
        )


class ELBv2ApplicationTargetGroupsLambda(ELBv2ApplicationTargetGroupsResponses):
    @property
    def name(self) -> str:
        return "elbv2_application_target_groups_lambda"

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        return self._get_metrics_with_specs(
            colleague_contents, ["lambda"], ["RequestCount", "LambdaUserError"]
        )


# .
#   .--Network ELB---------------------------------------------------------.
#   |     _   _      _                      _      _____ _     ____        |
#   |    | \ | | ___| |___      _____  _ __| | __ | ____| |   | __ )       |
#   |    |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / |  _| | |   |  _ \       |
#   |    | |\  |  __/ |_ \ V  V / (_) | |  |   <  | |___| |___| |_) |      |
#   |    |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |_____|_____|____/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBv2Network(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "elbv2_network"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, (load_balancer_dns_name, load_balancer) in enumerate(
            colleague_contents.content.items()
        ):
            load_balancer_dim = _elbv2_load_balancer_arn_to_dim(load_balancer["LoadBalancerArn"])
            for metric_name, stat in [
                ("ActiveFlowCount", "Average"),
                ("ActiveFlowCount_TLS", "Average"),
                ("ClientTLSNegotiationErrorCount", "Sum"),
                ("ConsumedLCUs", "Average"),
                ("NewFlowCount", "Sum"),
                ("NewFlowCount_TLS", "Sum"),
                ("ProcessedBytes", "Sum"),
                ("ProcessedBytes_TLS", "Sum"),
                ("TargetTLSNegotiationErrorCount", "Sum"),
                ("TCP_Client_Reset_Count", "Sum"),
                ("TCP_ELB_Reset_Count", "Sum"),
                ("TCP_Target_Reset_Count", "Sum"),
                # These two metrics are commented out because they need an additional dimension,
                # namely a target group, see https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-cloudwatch-metrics.html
                # the corresponding check aws_elbv2_network.healthy_hosts is currently also
                # commented out. The solution is to create a separate class specifically for
                # target groups of network load balancers and collect these metrics there.
                # ('HealthyHostCount', 'Maximum'),
                # ('UnHealthyHostCount', 'Maximum'),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": load_balancer_dns_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/NetworkELB",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {
                                        "Name": "LoadBalancer",
                                        "Value": load_balancer_dim,
                                    }
                                ],
                            },
                            "Period": self.period,
                            "Stat": stat,
                        },
                    }
                )
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


# .
#   .--RDS-----------------------------------------------------------------.
#   |                          ____  ____  ____                            |
#   |                         |  _ \|  _ \/ ___|                           |
#   |                         | |_) | | | \___ \                           |
#   |                         |  _ <| |_| |___) |                          |
#   |                         |_| \_\____/|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

AWSRDSLimitNameMap: Mapping[str, tuple[str, str]] = {
    "DBClusters": ("db_clusters", "DB clusters"),
    "DBClusterParameterGroups": ("db_cluster_parameter_groups", "DB cluster parameter groups"),
    "DBInstances": ("db_instances", "DB instances"),
    "EventSubscriptions": ("event_subscriptions", "Event subscriptions"),
    "ManualSnapshots": ("manual_snapshots", "Manual snapshots"),
    "OptionGroups": ("option_groups", "Option groups"),
    "DBParameterGroups": ("db_parameter_groups", "DB parameter groups"),
    "ReadReplicasPerMaster": ("read_replica_per_master", "Read replica per master"),
    "ReservedDBInstances": ("reserved_db_instances", "Reserved DB instances"),
    "DBSecurityGroups": ("db_security_groups", "DB security groups"),
    "DBSubnetGroups": ("db_subnet_groups", "DB subnet groups"),
    "SubnetsPerDBSubnetGroup": ("subnet_per_db_subnet_groups", "Subnet per DB subnet groups"),
    "AllocatedStorage": ("allocated_storage", "Allocated storage"),
    "AuthorizationsPerDBSecurityGroup": (
        "auths_per_db_security_groups",
        "Authorizations per DB security group",
    ),
    "DBClusterRoles": ("db_cluster_roles", "DB cluster roles"),
}


class RDSLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "rds_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        AWS/RDS API method 'describe_account_attributes' already sends
        limit and usage values.
        """
        response = self._client.describe_account_attributes()  # type: ignore[attr-defined]
        return self._get_response_content(response, "AccountQuotas")

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for limit in raw_content.content:
            quota_name = limit["AccountQuotaName"]
            key, title = AWSRDSLimitNameMap.get(quota_name, (None, None))
            if key is None or title is None:
                logging.info("%s: Unhandled account quota name: '%s'", self.name, quota_name)
                continue
            self._add_limit(
                "",
                AWSLimit(
                    key,
                    title,
                    int(limit["Max"]),
                    int(limit["Used"]),
                ),
            )
        return AWSComputedContent(None, 0.0)


class RDSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["rds_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["rds_tags"])

    @property
    def name(self) -> str:
        return "rds_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        db_instances = []

        for instance in self._describe_db_instances():
            tags = self._get_instance_tags(instance["DBInstanceArn"])
            if self._matches_tag_conditions(tags):
                instance["Region"] = self._region
                instance["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                db_instances.append(instance)

        return db_instances

    def _describe_db_instances(self):
        instances = []

        if self._names is None:
            for page in self._client.get_paginator("describe_db_instances").paginate():
                instances.extend(self._get_response_content(page, "DBInstances"))
            return instances

        for name in self._names:
            try:
                for page in self._client.get_paginator("describe_db_instances").paginate(
                    DBInstanceIdentifier=name
                ):
                    instances.extend(self._get_response_content(page, "DBInstances"))
            # NOTE: The suppression below is needed because of BaseClientExceptions.__getattr__ magic.
            except self._client.exceptions.DBInstanceNotFoundFault:  # type: ignore[misc]
                pass

        return instances

    def _get_instance_tags(self, instance_arn: str) -> Tags:
        # list_tags_for_resource cannot be paginated
        return self._get_response_content(
            self._client.list_tags_for_resource(ResourceName=instance_arn),  # type: ignore[attr-defined]
            "TagList",
        )

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            {instance["DBInstanceIdentifier"]: instance for instance in raw_content.content},
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class RDS(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._separator = " "

    @property
    def name(self) -> str:
        return "rds"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("rds_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        # the documentation
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MonitoringOverview.html
        # seems to be partially wrong: FailedSQLServerAgentJobsCount has to be queried in Counts
        # (instead of Count/Minute) and OldestReplicationSlotLag, ReplicationSlotDiskUsage and
        # TransactionLogsDiskUsage have to be queried in Bytes (instead of Megabytes)
        metrics: Metrics = []
        for idx, (instance_id, instance) in enumerate(colleague_contents.content.items()):
            for metric_name, stat, unit in [
                ("BinLogDiskUsage", "Average", "Bytes"),
                ("BurstBalance", "Average", "Percent"),
                ("CPUUtilization", "Average", "Percent"),
                ("CPUCreditUsage", "Average", "Count"),
                ("CPUCreditBalance", "Average", "Count"),
                ("DatabaseConnections", "Average", "Count"),
                ("DiskQueueDepth", "Average", "Count"),
                ("FailedSQLServerAgentJobsCount", "Sum", "Count"),
                ("NetworkReceiveThroughput", "Average", "Bytes/Second"),
                ("NetworkTransmitThroughput", "Average", "Bytes/Second"),
                ("OldestReplicationSlotLag", "Average", "Bytes"),
                ("ReadIOPS", "Average", "Count/Second"),
                ("ReadLatency", "Average", "Seconds"),
                ("ReadThroughput", "Average", "Bytes/Second"),
                ("ReplicaLag", "Average", "Seconds"),
                ("ReplicationSlotDiskUsage", "Average", "Bytes"),
                ("TransactionLogsDiskUsage", "Average", "Bytes"),
                ("TransactionLogsGeneration", "Average", "Bytes/Second"),
                ("WriteIOPS", "Average", "Count/Second"),
                ("WriteLatency", "Average", "Seconds"),
                ("WriteThroughput", "Average", "Bytes/Second"),
                # ("FreeableMemory", "Bytes"),
                # ("SwapUsage", "Bytes"),
                # ("FreeStorageSpace", "Bytes"),
                # ("MaximumUsedTransactionIDs", "Count"),
            ]:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": instance_id + self._separator + instance["Region"],
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "DBInstanceIdentifier",
                                    "Value": instance_id,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": stat,
                        "Unit": unit,
                    },
                }
                metrics.append(metric)
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for row in raw_content.content:
            instance_id = row["Label"].split(self._separator)[0]
            row.update(colleague_contents.content.get(instance_id, {}))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--CloudFront----------------------------------------------------------.
#   |          ____ _                 _ _____                _             |
#   |         / ___| | ___  _   _  __| |  ___| __ ___  _ __ | |_           |
#   |        | |   | |/ _ \| | | |/ _` | |_ | '__/ _ \| '_ \| __|          |
#   |        | |___| | (_) | |_| | (_| |  _|| | | (_) | | | | |_           |
#   |         \____|_|\___/ \__,_|\__,_|_|  |_|  \___/|_| |_|\__|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CloudFrontSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        tagging_client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._tagging_client = tagging_client
        self._names = self._config.service_config["cloudfront_names"]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["cloudfront_tags"]
        )

    @property
    def name(self) -> str:
        return "cloudfront_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        distributions = []

        resource_tags = fetch_resource_tags_from_types(
            self._tagging_client, ["cloudfront:distribution"]
        )

        for page in self._client.get_paginator("list_distributions").paginate():
            fetched_distributions = self._get_response_content(
                page, "DistributionList", dflt={}
            ).get("Items", [])
            distributions.extend(fetched_distributions)

        for distribution in distributions:
            distribution["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(
                resource_tags.get(distribution["ARN"], [])
            )

        if self._names:
            return [d for d in distributions if d["Id"] in self._names]

        if self._tags:
            distributions_arn_matching_tags = filter_resources_matching_tags(
                resource_tags,
                self._tags,
            )
            return [d for d in distributions if d["ARN"] in distributions_arn_matching_tags]

        return distributions

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class CloudFront(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        host_assignment: Literal["aws_host", "domain_host"],
        distributor: ResultDistributor | None = None,
    ):
        super().__init__(client, region, config, distributor=distributor)
        self.assign_to_origin_domain_host = host_assignment == "domain_host"

    @property
    def name(self) -> str:
        return "cloudfront_cloudwatch"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("cloudfront_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics = []
        for idx, instance in enumerate(colleague_contents.content):
            distribution_id = instance["Id"]
            for metric_name, stat, unit in [
                ("Requests", "Sum", "None"),
                ("BytesDownloaded", "Sum", "None"),
                ("BytesUploaded", "Sum", "None"),
                ("TotalErrorRate", "Average", "Percent"),
                ("4xxErrorRate", "Average", "Percent"),
                ("5xxErrorRate", "Average", "Percent"),
            ]:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": distribution_id,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/CloudFront",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "DistributionId",
                                    "Value": distribution_id,
                                },
                                {
                                    "Name": "Region",
                                    "Value": "Global",
                                },
                            ],
                        },
                        "Period": self.period,
                        "Stat": stat,
                        "Unit": unit,
                    },
                }
                metrics.append(metric)
        return metrics

    def _get_piggyback_host_by_distribution(
        self, cloudfront_summary: Sequence[Mapping]
    ) -> Mapping[str, str]:
        if not cloudfront_summary:
            return {}

        host_by_distribution: dict[str, str] = {}
        for distribution_data in cloudfront_summary:
            distribution_id = distribution_data.get("Id")
            origins = distribution_data.get("Origins", {}).get("Items")
            if not distribution_id or not origins:
                continue
            distribution_origin = origins[0].get("DomainName", "")
            host_by_distribution[distribution_id] = distribution_origin
        return host_by_distribution

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_host = defaultdict(list)
        host_by_distribution: Mapping[str, str] = {}
        if self.assign_to_origin_domain_host:
            host_by_distribution = self._get_piggyback_host_by_distribution(
                colleague_contents.content
            )
        for distribution_data in raw_content.content:
            distribution_id = distribution_data.get("Label", "")
            piggyback_host = host_by_distribution.get(distribution_id, "")
            content_by_host[piggyback_host].append(distribution_data)
        return AWSComputedContent(content_by_host, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_host, content)
            for piggyback_host, content in computed_content.content.items()
        ]


# .
#   .--Cloudwatch----------------------------------------------------------.
#   |         ____ _                 _               _       _             |
#   |        / ___| | ___  _   _  __| |_      ____ _| |_ ___| |__          |
#   |       | |   | |/ _ \| | | |/ _` \ \ /\ / / _` | __/ __| '_ \         |
#   |       | |___| | (_) | |_| | (_| |\ V  V / (_| | || (__| | | |        |
#   |        \____|_|\___/ \__,_|\__,_| \_/\_/ \__,_|\__\___|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CloudwatchAlarmsLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "cloudwatch_alarms_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        return list(_describe_alarms(self._client, self._get_response_content))

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        self._add_limit(
            "",
            AWSLimit(
                "cloudwatch_alarms",
                "CloudWatch Alarms",
                5000,
                len(raw_content.content),
            ),
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class CloudwatchAlarms(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["cloudwatch_alarms"]

    @property
    def name(self) -> str:
        return "cloudwatch_alarms"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("cloudwatch_alarms_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        if self._names:
            if colleague_contents.content:
                return [
                    alarm
                    for alarm in colleague_contents.content
                    if alarm["AlarmName"] in self._names
                ]
            return list(
                _describe_alarms(self._client, self._get_response_content, names=self._names)
            )
        return list(_describe_alarms(self._client, self._get_response_content))

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        if raw_content.content:
            return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)
        dflt_alarms = [{"AlarmName": "Check_MK/CloudWatch Alarms", "StateValue": "NO_ALARMS"}]
        return AWSComputedContent(dflt_alarms, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--DynamoDB------------------------------------------------------------.
#   |         ____                                    ____  ____           |
#   |        |  _ \ _   _ _ __   __ _ _ __ ___   ___ |  _ \| __ )          |
#   |        | | | | | | | '_ \ / _` | '_ ` _ \ / _ \| | | |  _ \          |
#   |        | |_| | |_| | | | | (_| | | | | | | (_) | |_| | |_) |         |
#   |        |____/ \__, |_| |_|\__,_|_| |_| |_|\___/|____/|____/          |
#   |               |___/                                                  |
#   '----------------------------------------------------------------------'


class DynamoDB(AWSSection):
    @property
    def name(self) -> str:
        return "dynamodb"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    @property
    def host_labels(self) -> Mapping[str, str]:
        return {"cmk/aws/service": "dynamodb"}

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, str]] | None:
        (colleague_contents,) = args
        return colleague_contents.content

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("dynamodb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in colleague_contents.content:
            content_by_piggyback_hosts.setdefault(row, []).append(row)

        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows, self.host_labels)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class DynamoDBLabelsGeneric(AWSSectionLabels):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
        resource: str = "",
    ) -> None:
        self._resource = resource
        super().__init__(client, region, config, distributor=distributor)

    @property
    def name(self) -> str:
        return "%s_generic_labels" % self._resource

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("%s_summary" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> object:
        (colleague_contents,) = args
        return colleague_contents.content

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        computed_content = {
            elb_instance_id: data.get("TagsForCmkLabels")
            for elb_instance_id, data in raw_content.content.items()
            if data.get("TagsForCmkLabels")
        }
        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class DynamoDBLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "dynamodb_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        The AWS/DynamoDB API method 'describe_limits' provides limits only, but no usage data. We
        therefore gather a list of tables using the method 'list_tables' and check the usage of each
        table via 'describe_table'. See also
        https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_DescribeLimits.html.
        """
        limits = self._client.describe_limits()  # type: ignore[attr-defined]
        tables = _describe_dynamodb_tables(self._client, self._get_response_content)
        return tables, limits

    def _add_read_write_limits(
        self,
        piggyback_hostname: str,
        read_usage: int,
        write_usage: int,
        read_limit: int,
        write_limit: int,
    ) -> None:
        self._add_limit(
            piggyback_hostname,
            AWSLimit(
                "read_capacity",
                "Read Capacity",
                read_limit,
                read_usage,
            ),
        )

        self._add_limit(
            piggyback_hostname,
            AWSLimit(
                "write_capacity",
                "Write Capacity",
                write_limit,
                write_usage,
            ),
        )

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        tables, limits = raw_content.content
        account_read_usage = 0
        account_write_usage = 0

        for table in tables:
            key_usage = "ProvisionedThroughput"
            table_usage_read = table[key_usage]["ReadCapacityUnits"]
            table_usage_write = table[key_usage]["WriteCapacityUnits"]

            # in this case we have an on-demand table, which has no set values for read/write;
            # provisioned tables have a minimum of 1 here
            if table_usage_read == table_usage_write == 0:
                continue

            for global_sec_index in table.get("GlobalSecondaryIndexes", []):
                table_usage_read += global_sec_index[key_usage]["ReadCapacityUnits"]
                table_usage_write += global_sec_index[key_usage]["WriteCapacityUnits"]

            account_read_usage += table_usage_read
            account_write_usage += table_usage_write

            self._add_read_write_limits(
                _hostname_from_name_and_region(table["TableName"], self._region),
                table_usage_read,
                table_usage_write,
                limits["TableMaxReadCapacityUnits"],
                limits["TableMaxWriteCapacityUnits"],
            )

        self._add_limit(
            "",
            AWSLimit(
                "number_of_tables",
                "Number of tables",
                256,  # describe_limits does not provide limits for this
                len(tables),
            ),
        )
        self._add_read_write_limits(
            "",
            account_read_usage,
            account_write_usage,
            limits["AccountMaxReadCapacityUnits"],
            limits["AccountMaxWriteCapacityUnits"],
        )

        return AWSComputedContent(tables, raw_content.cache_timestamp)


class DynamoDBSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["dynamodb_names"]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["dynamodb_tags"]
        )

    @property
    def name(self) -> str:
        return "dynamodb_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("dynamodb_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        (colleague_contents,) = args

        found_tables = []

        for table in self._describe_tables(colleague_contents):
            assert isinstance(table["TableArn"], str)
            tags = self._get_table_tags(table["TableArn"])

            if self._matches_tag_conditions(tags):
                table["Region"] = self._region
                table["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                found_tables.append(table)

        return found_tables

    def _get_table_tags(self, table_arn: str) -> Tags:
        tags = []
        paginator = self._client.get_paginator("list_tags_of_resource")
        response_iterator = paginator.paginate(ResourceArn=table_arn)
        for page in response_iterator:
            tags.extend(self._get_response_content(page, "Tags"))
        return tags

    def _describe_tables(
        self, colleague_contents: AWSColleagueContents
    ) -> Sequence[dict[str, object]]:
        if self._names is None:
            if colleague_contents.content:
                return colleague_contents.content
            return _describe_dynamodb_tables(self._client, self._get_response_content)

        if colleague_contents.content:
            return [
                table for table in colleague_contents.content if table["TableName"] in self._names
            ]
        return _describe_dynamodb_tables(
            self._client, self._get_response_content, fetched_table_names=self._names
        )

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, str] = {}
        for table in raw_content.content:
            content_by_piggyback_hosts.setdefault(
                _hostname_from_name_and_region(table["TableName"], self._region), table
            )
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class DynamoDBTable(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "dynamodb_table"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("dynamodb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []

        for idx, (piggyback_hostname, table) in enumerate(colleague_contents.content.items()):
            for metric_name, stat, operation_dim, unit in [
                ("ConsumedReadCapacityUnits", "Minimum", "", "Count"),
                ("ConsumedReadCapacityUnits", "Maximum", "", "Count"),
                ("ConsumedReadCapacityUnits", "Sum", "", "Count"),
                ("ConsumedWriteCapacityUnits", "Minimum", "", "Count"),
                ("ConsumedWriteCapacityUnits", "Maximum", "", "Count"),
                ("ConsumedWriteCapacityUnits", "Sum", "", "Count"),
                ("SuccessfulRequestLatency", "Maximum", "Query", "Milliseconds"),
                ("SuccessfulRequestLatency", "Average", "Query", "Milliseconds"),
                ("SuccessfulRequestLatency", "Maximum", "GetItem", "Milliseconds"),
                ("SuccessfulRequestLatency", "Average", "GetItem", "Milliseconds"),
                ("SuccessfulRequestLatency", "Maximum", "PutItem", "Milliseconds"),
                ("SuccessfulRequestLatency", "Average", "PutItem", "Milliseconds"),
            ]:
                dimensions: list[Dimension] = [{"Name": "TableName", "Value": table["TableName"]}]

                if operation_dim:
                    dimensions.append({"Name": "Operation", "Value": operation_dim})
                    ident = self._create_id_for_metric_data_query(
                        idx, metric_name, operation_dim, stat
                    )
                else:
                    ident = self._create_id_for_metric_data_query(idx, metric_name, stat)

                metrics.append(
                    {
                        "Id": ident,
                        "Label": piggyback_hostname,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/DynamoDB",
                                "MetricName": metric_name,
                                "Dimensions": dimensions,
                            },
                            "Period": self.period,
                            "Stat": stat,
                            "Unit": unit,
                        },
                    }
                )

        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[dict[str, object]]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)

        key_provisioned_capacity = "ProvisionedThroughput"
        for piggyback_hostname, table in colleague_contents.content.items():
            content_by_piggyback_hosts[piggyback_hostname].append(
                {
                    "provisioned_ReadCapacityUnits": table[key_provisioned_capacity][
                        "ReadCapacityUnits"
                    ],
                    "provisioned_WriteCapacityUnits": table[key_provisioned_capacity][
                        "WriteCapacityUnits"
                    ],
                }
            )

        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


# .
#   .--WAFV2---------------------------------------------------------------.
#   |                __        ___    _______     ______                   |
#   |                \ \      / / \  |  ___\ \   / /___ \                  |
#   |                 \ \ /\ / / _ \ | |_   \ \ / /  __) |                 |
#   |                  \ V  V / ___ \|  _|   \ V /  / __/                  |
#   |                   \_/\_/_/   \_\_|      \_/  |_____|                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class WAFV2Limits(AWSSectionLimits):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        scope: Scope,
        distributor: ResultDistributor | None = None,
        quota_client: BaseClient | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor, quota_client=quota_client)
        self._region_report = _validate_wafv2_scope_and_region(scope, self._region)
        self._scope = scope

    @property
    def name(self) -> str:
        return "wafv2_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        We get lists of the following resources, since they have per-region limits:
        - Web Access Control Lists (Web ACLs)
        - Rule groups
        - IP sets
        - Regex sets
        Additionally, we gather more information about the Web ACLs, since they additionally have
        limits on how many rules they can use.
        """

        resources: dict = {}

        for list_operation, key in [
            (self._client.list_web_acls, "WebACLs"),  # type: ignore[attr-defined]
            (self._client.list_rule_groups, "RuleGroups"),  # type: ignore[attr-defined]
            (self._client.list_ip_sets, "IPSets"),  # type: ignore[attr-defined]
            (self._client.list_regex_pattern_sets, "RegexPatternSets"),  # type: ignore[attr-defined]
        ]:
            resources[key] = _iterate_through_wafv2_list_operations(
                list_operation, self._scope, key, self._get_response_content
            )

        web_acls = _get_wafv2_web_acls(
            self._client,
            self._scope,
            self._get_response_content,
            web_acls_info=resources["WebACLs"],
        )

        return resources, web_acls

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        """
        See https://docs.aws.amazon.com/waf/latest/developerguide/limits.html for the limits. The
        page says that the limits can be changed, however, the API does not seem to offer a method
        for getting the current limits, so we have to hard-code the default values.
        """

        resources, web_acls = raw_content.content

        # region-wide limits
        for resource_key, limit_key, limit_title, def_limit in [
            ("WebACLs", "web_acls", "Web ACLs", 100),
            ("RuleGroups", "rule_groups", "Rule groups", 100),
            ("IPSets", "ip_sets", "IP sets", 100),
            ("RegexPatternSets", "regex_pattern_sets", "Regex sets", 10),
        ]:
            self._add_limit(
                "",
                AWSLimit(limit_key, limit_title, def_limit, len(resources[resource_key])),
                region=self._region_report,
            )

        # limits per Web ACL
        for web_acl in web_acls:
            self._add_limit(
                _hostname_from_name_and_region(web_acl["Name"], self._region_report),
                AWSLimit(
                    "web_acl_capacity_units",
                    "Web ACL capacity units (WCUs)",
                    1500,
                    web_acl["Capacity"],
                ),
                region=self._region_report,
            )

        return AWSComputedContent(web_acls, raw_content.cache_timestamp)


class WAFV2Summary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        scope: Scope,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._region_report = _validate_wafv2_scope_and_region(scope, self._region)
        self._scope = scope
        self._names = self._config.service_config["wafv2_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["wafv2_tags"])

    @property
    def name(self) -> str:
        return "wafv2_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("wafv2_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        (colleague_contents,) = args
        found_web_acls = []

        for web_acl in self._describe_web_acls(colleague_contents):
            # list_tags_for_resource does not support pagination
            tag_info = self._get_response_content(
                self._client.list_tags_for_resource(ResourceARN=web_acl["ARN"]),  # type: ignore[attr-defined]
                "TagInfoForResource",
                dflt={},
            )
            tags = self._get_response_content(tag_info, "TagList")

            if self._matches_tag_conditions(tags):
                web_acl["Region"] = self._region_report
                web_acl["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                found_web_acls.append(web_acl)

        return found_web_acls

    def _describe_web_acls(
        self, colleague_contents: AWSColleagueContents
    ) -> Sequence[dict[str, object]]:
        if self._names is None:
            if colleague_contents.content:
                return colleague_contents.content
            return _get_wafv2_web_acls(self._client, self._scope, self._get_response_content)

        if colleague_contents.content:
            return [
                web_acl for web_acl in colleague_contents.content if web_acl["Name"] in self._names
            ]
        return _get_wafv2_web_acls(
            self._client, self._scope, self._get_response_content, web_acls_names=self._names
        )

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, str] = {}
        for web_acl in raw_content.content:
            content_by_piggyback_hosts.setdefault(
                _hostname_from_name_and_region(web_acl["Name"], self._region_report), web_acl
            )
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class WAFV2WebACL(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        is_regional: bool,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        if not is_regional:
            assert self._region == "us-east-1", (
                "WAFV2WebACL: is_regional should only be set to "
                "False in combination with the region us-east-1, "
                "since metrics for CloudFront-WAFs can only be "
                "accessed from this region"
            )

        self._static_metric_dimensions: Collection[Dimension] = [{"Name": "Rule", "Value": "ALL"}]
        if is_regional:
            self._static_metric_dimensions = [
                *self._static_metric_dimensions,
                {"Name": "Region", "Value": self._region},
            ]

    @property
    def name(self) -> str:
        return "wafv2_web_acl"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("wafv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []

        for idx, (piggyback_hostname, web_acl) in enumerate(colleague_contents.content.items()):
            for metric_name in ["AllowedRequests", "BlockedRequests"]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": piggyback_hostname,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/WAFV2",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {"Name": "WebACL", "Value": web_acl["Name"]},
                                    *self._static_metric_dimensions,
                                ],
                            },
                            "Period": self.period,
                            "Stat": "Sum",
                        },
                    }
                )

        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[dict[str, object]]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


# .
#   .--Lambda--------------------------------------------------------------.
#   |               _                    _         _                       |
#   |              | |    __ _ _ __ ___ | |__   __| | __ _                 |
#   |              | |   / _` | '_ ` _ \| '_ \ / _` |/ _` |                |
#   |              | |__| (_| | | | | | | |_) | (_| | (_| |                |
#   |              |_____\__,_|_| |_| |_|_.__/ \__,_|\__,_|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'
ProvisionedConcurrencyConfigs = Mapping[str, Sequence[Mapping[str, str]]]


class LambdaRegionLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "lambda_region_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        return self._client.get_account_settings()  # type: ignore[attr-defined]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        limits = raw_content.content
        self._add_limit(
            "",
            AWSLimit(
                "total_code_size",
                "Total Code Size",
                100,
                int(limits["AccountLimit"]["TotalCodeSize"]),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                "concurrent_executions",
                "Concurrent Executions",
                100,
                int(limits["AccountLimit"]["ConcurrentExecutions"]),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                "unreserved_concurrent_executions",
                "Unreserved Concurrent Executions",
                100,
                int(limits["AccountLimit"]["UnreservedConcurrentExecutions"]),
            ),
            region=self._region,
        )
        return AWSComputedContent(limits, raw_content.cache_timestamp)


class LambdaSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["lambda_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["lambda_tags"])

    @property
    def name(self) -> str:
        return "lambda_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
        functions = []
        for page in self._client.get_paginator("list_functions").paginate():
            for function in self._get_response_content(page, "Functions"):
                tags = self._get_tagging_for(function.get("FunctionArn"))
                if (
                    self._names is None
                    or (self._names and function.get("FunctionName") in self._names)
                ) and (self._tags is None or self._tags and self._matches_tag_conditions(tags)):
                    function["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                    functions.append(function)
        return functions

    def _get_tagging_for(self, function_arn: str) -> Tags:
        tagging = self._get_response_content(self._client.list_tags(Resource=function_arn), "Tags")  # type: ignore[attr-defined]
        # adapt to format of _prepare_tags_for_api_response
        return [{"Key": key, "Value": value} for key, value in tagging.items()]

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


def _function_arn_to_function_name_dim(function_arn: str) -> str:
    """
    >>> _function_arn_to_function_name_dim("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function")
    'my_python_test_function'
    """
    return function_arn.split(":")[6]


class LambdaCloudwatch(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "lambda"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        # lambda_provisioned_concurrency has to be used, because some metrics for provisioned concurrency will only
        # be reported if the ARN for the provisioned concurrency configuration is used.
        # lambda_provisioned_concurrency contains also the ARNs for lambda functions without provisioned conurrency.
        colleague = self._received_results.get("lambda_provisioned_concurrency")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        def _get_function_arns(colleague_content: dict) -> Sequence[str]:
            function_arns = []
            for function_arn, provisioned_concurrency_configurations in colleague_content.items():
                for config in provisioned_concurrency_configurations:
                    function_arns.append(config["FunctionArn"])
                function_arns.append(function_arn)
            return function_arns

        def _create_dimensions(function_arn: str) -> Sequence[Dimension]:
            def _function_arn_to_resource_dim(function_arn: str) -> str | None:
                """
                >>> _function_arn_to_resource_dim("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function:AliasOrVersionNumber")
                'my_python_test_function:AliasOrVersionNumber'
                """
                splitted = function_arn.split(":")
                return f"{splitted[6]}:{splitted[7]}" if len(splitted) == 8 else None

            dimensions: list[Dimension] = [
                {
                    "Name": "FunctionName",
                    "Value": _function_arn_to_function_name_dim(function_arn),
                }
            ]
            if resource_dim := _function_arn_to_resource_dim(function_arn):
                dimensions.append(
                    {
                        "Name": "Resource",
                        "Value": resource_dim,
                    }
                )
            return dimensions

        metrics = [
            ("ConcurrentExecutions", "Count", "Maximum"),
            ("DeadLetterErrors", "Count", "Sum"),
            ("DestinationDeliveryFailures", "Count", "Sum"),
            ("Duration", "Milliseconds", "Average"),
            ("Errors", "Count", "Sum"),
            ("Invocations", "Count", "Sum"),
            ("IteratorAge", "Count", "Average"),
            ("PostRuntimeExtensionsDuration", "Count", "Average"),
            ("ProvisionedConcurrencyInvocations", "Count", "Sum"),
            ("ProvisionedConcurrencySpilloverInvocations", "Count", "Sum"),
            ("ProvisionedConcurrencyUtilization", "Count", "Average"),
            ("ProvisionedConcurrentExecutions", "Count", "Sum"),
            ("Throttles", "Count", "Sum"),
            ("UnreservedConcurrentExecutions", "Count", "Maximum"),
        ]
        return [
            {
                "Id": self._create_id_for_metric_data_query(idx, metric_name),
                "Label": function_arn,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Lambda",
                        "MetricName": metric_name,
                        "Dimensions": _create_dimensions(function_arn),
                    },
                    "Period": self.period,
                    "Stat": stat,
                    "Unit": unit,
                },
            }
            for idx, function_arn in enumerate(_get_function_arns(colleague_contents.content))
            for metric_name, unit, stat in metrics
        ]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class LambdaProvisionedConcurrency(AWSSection):
    @property
    def name(self) -> str:
        return "lambda_provisioned_concurrency"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("lambda_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _list_provisioned_concurrency_configs(
        self, function_name: str
    ) -> Sequence[Mapping[str, str]]:
        return [
            config
            for page in self._client.get_paginator("list_provisioned_concurrency_configs").paginate(
                FunctionName=function_name
            )
            for config in self._get_response_content(page, "ProvisionedConcurrencyConfigs")
        ]

    def get_live_data(self, *args: AWSColleagueContents) -> ProvisionedConcurrencyConfigs:
        (colleague_contents,) = args
        return {
            lambda_function["FunctionArn"]: self._list_provisioned_concurrency_configs(
                lambda_function["FunctionName"]
            )
            for lambda_function in colleague_contents.content
        }

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]

    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


LambdaMetricStats = Sequence[Mapping[str, str]]


class LambdaCloudwatchInsights(AWSSection):
    # The maximum number of log groups that can be queried with a single API call - source:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html#CloudWatchLogs.Client.start_query
    MAX_LOG_GROUPS_PER_QUERY = 20

    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["lambda_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["lambda_tags"])

    @property
    def name(self) -> str:
        return "lambda_cloudwatch_insights"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        # lambda_provisioned_concurrency has to be used, because some metrics for provisioned concurrency will only
        # be reported if the ARN for the provisioned concurrency configuration is used.
        # lambda_provisioned_concurrency contains also the ARNs for lambda functions without provisioned conurrency.
        colleague = self._received_results.get("lambda_provisioned_concurrency")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @staticmethod
    def query_results(
        *,
        client: "CloudWatchLogsClient",
        query_id: str,
        timeout_seconds: float,
        sleep_duration: float = 0.5,
    ) -> Sequence[LambdaMetricStats] | None:
        "Synchronous wrapper for asynchronous query API with timeout checking. (agent should not be blocked)."
        response_results: dict = {"status": "Scheduled"}
        query_start = datetime.now().timestamp()
        while response_results["status"] != "Complete":
            response_results = client.get_query_results(queryId=query_id)  # type: ignore[assignment]
            if datetime.now().timestamp() - query_start >= timeout_seconds:
                client.stop_query(queryId=query_id)
                logging.error(
                    "LambdaCloudwatchInsights: query_results failed"
                    " or timed out with the following results: %s ",
                    response_results["results"],
                )
                break
            sleep(sleep_duration)
        # stat metrics are always in the first element of the results or an empty list
        return (
            response_results["results"]
            if response_results["results"] and response_results["status"] == "Complete"
            else None
        )

    def _group_query_results_by_function(
        self, query_results: Sequence[LambdaMetricStats]
    ) -> dict[str, LambdaMetricStats]:
        grouped_results: dict[str, LambdaMetricStats] = {}
        for query_result in query_results:
            if not query_result:
                continue
            log_name = [e["value"] for e in query_result if e["field"] == "@log"][0]
            lambda_fn_name = log_name.split("/")[-1]
            final_query_result = [e for e in query_result if e["field"] != "@log"]
            grouped_results[lambda_fn_name] = final_query_result
        return grouped_results

    def _start_logwatch_query(self, *, log_group_names: list[str], query_string: str) -> str:
        end_time_seconds = int(NOW.timestamp())
        start_time_seconds = int(end_time_seconds - self.period)
        response_query_id = self._client.start_query(  # type: ignore[attr-defined]
            logGroupNames=log_group_names,
            startTime=start_time_seconds,
            endTime=end_time_seconds,
            queryString=query_string,
        )
        return response_query_id["queryId"]

    def _get_splitted_list(self, source_list: list[T], chunk_size: int) -> list[list[T]]:
        """
        Split a list into a list of lists where every nested list has a maximum size of `chunk_size`
        """
        return [source_list[i : i + chunk_size] for i in range(0, len(source_list), chunk_size)]

    def _get_all_existing_lambda_log_groups(self) -> set[str]:
        """
        Fetches all the existing log groups in the AWS account that are related to lambda functions
        """
        log_groups: set[str] = set()
        for page in self._client.get_paginator("describe_log_groups").paginate(
            logGroupNamePrefix="/aws/lambda/"
        ):
            log_groups.update(
                e["logGroupName"] for e in self._get_response_content(page, "logGroups")
            )
        return log_groups

    def _get_existing_log_groups_for_functions(self, function_names: Iterable[str]) -> list[str]:
        # We are getting all the existing log groups because we want to query logwatch for multiple
        # log groups at once but the query fails if one of the log groups don't exist so what might
        # happen is that we query log groups for 2 functions: 1 that has an existing log group and 1
        # that doesn't have it, in that case the query fails and we are not getting the data for the
        # function with a log group.
        # To prevent this, we just query the log groups that exists by checking that before doing
        # the actual query.
        all_existing_log_groups = self._get_all_existing_lambda_log_groups()
        functions_log_groups = [f"/aws/lambda/{fn_name}" for fn_name in function_names]
        # `all_existing_log_groups` may contain log groups for lambda functions that don't exist
        # anymore so we are filtering it to just have the log groups for the existing functions
        return [e for e in functions_log_groups if e in all_existing_log_groups]

    def get_live_data(self, *args: AWSColleagueContents) -> Mapping[str, LambdaMetricStats] | None:
        (colleague_contents,) = args

        function_name_to_arn: dict[str, str] = {
            _function_arn_to_function_name_dim(fn_arn): fn_arn
            for fn_arn in colleague_contents.content.keys()
        }
        existing_functions_log_groups = self._get_existing_log_groups_for_functions(
            function_name_to_arn.keys()
        )
        chunked_log_groups: list[list[str]] = self._get_splitted_list(
            existing_functions_log_groups, self.MAX_LOG_GROUPS_PER_QUERY
        )

        queries: list[str] = []
        # Logwatch queries are async jobs so we are first starting all of them and then getting the
        # result for all of them so that they will be processed in parallel by AWS
        for curr_log_groups in chunked_log_groups:
            query_id = self._start_logwatch_query(
                log_group_names=curr_log_groups,
                query_string='filter @type = "REPORT"'
                "| stats "
                "max(@maxMemoryUsed) as max_memory_used_bytes,"
                "max(@initDuration) as max_init_duration_ms,"
                'sum(strcontains(@message, "Init Duration")) as count_cold_starts,'
                "count() as count_invocations "
                "by @log",
            )
            queries.append(query_id)

        cloudwatch_data: dict[str, LambdaMetricStats] = {}
        for query_id in queries:
            query_results = self.query_results(
                client=self._client,  # type: ignore[arg-type]
                query_id=query_id,
                timeout_seconds=60,
            )
            if not query_results:
                continue
            current_data = self._group_query_results_by_function(query_results)
            for fn_name, fn_stats in current_data.items():
                fn_arn = function_name_to_arn[fn_name]
                cloudwatch_data[fn_arn] = fn_stats
        return cloudwatch_data

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]

    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


# .
#   .--Route53-------------------------------------------------------------.
#   |                                  _       ____ _____                  |
#   |                  _ __ ___  _   _| |_ ___| ___|___ /                  |
#   |                 | '__/ _ \| | | | __/ _ \___ \ |_ \                  |
#   |                 | | | (_) | |_| | ||  __/___) |__) |                 |
#   |                 |_|  \___/ \__,_|\__\___|____/____/                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class HealthCheckConfig(TypedDict, total=False):
    Port: int
    type: str
    FullyQualifiedDomainName: str
    RequestInterval: int
    FailureThreshold: int
    MeasureLatency: bool
    Inverted: bool
    Disabled: bool
    EnableSNI: bool


class HealthCheck(TypedDict, total=False):
    Id: str
    CallerReference: str
    HealthCheckConfig: HealthCheckConfig
    HealthCheckVersion: int


class Route53HealthChecks(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)

    @property
    def name(self) -> str:
        return "route53_health_checks"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[HealthCheck]:
        return list(
            itertools.chain.from_iterable(
                self._get_response_content(page, "HealthChecks")
                for page in self._client.get_paginator("list_health_checks").paginate()
            )
        )

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class Route53Cloudwatch(AWSSectionCloudwatch):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=None)

    @property
    def name(self) -> str:
        return "route53_cloudwatch"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("route53_health_checks")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        health_checks: Sequence[HealthCheck] = colleague_contents.content
        return [
            {
                "Id": self._create_id_for_metric_data_query(idx, metric_name),
                "Label": health_check["Id"],
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Route53",
                        "MetricName": metric_name,
                        "Dimensions": [
                            {
                                "Name": "HealthCheckId",
                                "Value": health_check["Id"],
                            }
                        ],
                    },
                    "Period": self.period,
                    "Stat": stat,
                    "Unit": unit,
                },
            }
            for idx, health_check in enumerate(health_checks)
            for metric_name, unit, stat in [
                ("ChildHealthCheckHealthyCount", "Count", "Average"),
                ("ConnectionTime", "Milliseconds", "Average"),
                ("HealthCheckPercentageHealthy", "Percent", "Average"),
                ("HealthCheckStatus", "None", "Maximum"),
                ("SSLHandshakeTime", "Milliseconds", "Average"),
                ("TimeToFirstByte", "Milliseconds", "Average"),
            ]
        ]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", rows) for _id, rows in computed_content.content.items()]


#   .--SNS-----------------------------------------------------------------.
#   |                          ____  _   _ ____                            |
#   |                         / ___|| \ | / ___|                           |
#   |                         \___ \|  \| \___ \                           |
#   |                          ___) | |\  |___) |                          |
#   |                         |____/|_| \_|____/                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
# SNS is a messaging service that follows the event-producers -> topics -> subscriptions model
# producers and topics have a many-to-many-relationship.
# topics and subscriptions also have a many-to-many-relationship.
# It therefore makes sense to monitor Subscriptions, Topics, and Producers as the three central
# building blocks of AWS SNS. Subscriptions and Topics have specific limits per account so they
# are handled in the limits section. For producers it is more important to look at what exactly
# they are producing, so the cloudwatch section monitors detailed metrics about incoming traffic.


@dataclass(frozen=True)
class SNSTopic:
    region: str
    account_id: str
    topic_name: str

    @classmethod
    def from_arn(cls: type["SNSTopic"], arn_str: str) -> "SNSTopic":
        """Example topic ARN: 'arn:aws:sns:eu-central-1:710145618630:TestTopicGiordano'"""
        splitted_arn = arn_str.split(":")
        return cls(region=splitted_arn[3], account_id=splitted_arn[4], topic_name=splitted_arn[5])

    def to_arn(self) -> str:
        return f"arn:aws:sns:{self.region}:{self.account_id}:{self.topic_name}"

    def to_item_id(self) -> str:
        """Return the item id of the CheckMK service."""
        # !!!DO NOT CHANGE THE ITEM ID!!!!
        # If you change the item id, it will create new services and lose all the data of the old
        # services because the service name will change according to the item id

        # SNS Topic name is unique per region so we need to include the region name in the service
        # name to avoid considering 2 topics with the same name in different regions as the same
        # topic
        return f"{self.topic_name} [{self.region}]"


class SNSTopicsFetcher:
    """This class will fetch the topics matching the config criteria and cache them in memory"""

    def __init__(
        self,
        client: BaseClient,
        tagging_client: BaseClient,
        region: str,
        config: AWSConfig,
    ):
        self._client = client
        self._tagging_client = tagging_client
        self._region = region
        self._names = config.service_config["sns_names"]
        self._tags = AWSSection.prepare_tags_for_api_response(config.service_config["sns_tags"])

    def fetch_all_topics(self) -> list[SNSTopic]:
        return [
            SNSTopic.from_arn(topic["TopicArn"])
            for page in self._client.get_paginator("list_topics").paginate()
            for topic in page["Topics"]
        ]

    def fetch_all_topic_tags(self) -> ResourceTags:
        return fetch_resource_tags_from_types(self._tagging_client, ["sns:topic"])

    def filter_topics(self, all_topics_arns: list[str], resource_tags: ResourceTags) -> list[str]:
        if self._tags:
            topics_arn_matching_tags = filter_resources_matching_tags(resource_tags, self._tags)
            return [t for t in all_topics_arns if t in topics_arn_matching_tags]

        if self._names:
            return [t for t in all_topics_arns if SNSTopic.from_arn(t).topic_name in self._names]

        return all_topics_arns


class SNSLimits(AWSSectionLimits):
    """
    AWS imposes the following per account limits.
    Topics (Standard): 100k
    Topics (FIFO): 1k
    Subscriptions (Standard): 12.5M
    Subscriptions (FIFO): 100
    There are many other limits related to how many API requests one can make per second for
    various tasks, but these four limits above are the most account-relevant limits.
    This article might also be a valuable resource: https://www.serverless.com/guides/amazon-sns#:~:text=Amazon%20SNS%20limits,-%E2%80%8D&text=Both%20subscribe%20and%20unsubscribe%20transactions,the%20us%2Deast%2D1%20region
    """

    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        sns_topics_fetcher: SNSTopicsFetcher,
        distributor: ResultDistributor | None = None,
    ):
        super().__init__(client, region, config, distributor=distributor)
        self._sns_topics_fetcher = sns_topics_fetcher

    @property
    def name(self) -> str:
        return "sns_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping]:
        # We don't want to filter by name and tags for the limits section since the filtered topics
        # are considered in the AWS account limits
        topics = self._sns_topics_fetcher.fetch_all_topics()

        num_of_subscriptions_by_topic = Counter(
            str(subscription["TopicArn"])
            for page in self._client.get_paginator("list_subscriptions").paginate()
            for subscription in page["Subscriptions"]
        )

        return [
            {
                "arn": topic.to_arn(),
                "is_fifo": topic.topic_name.endswith(".fifo"),
                "num_subscriptions": num_of_subscriptions_by_topic[topic.to_arn()],
            }
            for topic in topics
        ]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        topics: Sequence[Mapping] = raw_content.content

        self._add_limit(
            "",
            AWSLimit(
                key="topics_standard",
                title="Standard Topics",
                limit=int(100e3),
                amount=sum(not x["is_fifo"] for x in topics),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                key="topics_fifo",
                title="FIFO Topics",
                limit=int(1e3),
                amount=sum(x["is_fifo"] for x in topics),
            ),
            region=self._region,
        )

        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class SNSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        sns_topics_fetcher: SNSTopicsFetcher,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._sns_topics_fetcher = sns_topics_fetcher

    @property
    def name(self) -> str:
        return "sns_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("sns_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        (colleague_contents,) = args

        if colleague_contents.content:
            topics_arn = [topic["arn"] for topic in colleague_contents.content]
        else:
            topics_arn = [topic.to_arn() for topic in self._sns_topics_fetcher.fetch_all_topics()]

        tags = self._sns_topics_fetcher.fetch_all_topic_tags()
        filtered_topics = self._sns_topics_fetcher.filter_topics(topics_arn, tags)

        found_topics = []
        for topic_arn in topics_arn:
            if topic_arn in filtered_topics:
                topic = SNSTopic.from_arn(topic_arn)
                found_topics.append(
                    {
                        "Name": topic.topic_name,
                        "ARN": topic_arn,
                        "ItemId": topic.to_item_id(),
                        "Region": topic.region,
                        "AccountId": topic.account_id,
                        "TagsForCmkLabels": self.process_tags_for_cmk_labels(
                            tags.get(topic_arn, [])
                        ),
                    }
                )

        return found_topics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class SNSSMS(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "sns_sms_cloudwatch"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        # The metrics of this class are grouped by AWS region because AWS doesn't provide SMS-relatd
        # metrics on a per-topic level but only per-region
        sms_success_rate_metric: Metric = {
            "Id": self._create_id_for_metric_data_query(0, "SMSSuccessRate"),
            "Label": self.region,
            "Period": self.period,
            "Expression": 'SELECT AVG(SMSSuccessRate) FROM SCHEMA("AWS/SNS", Country,SMSType)',
        }
        sms_spending_metric: Metric = {
            "Id": self._create_id_for_metric_data_query(0, "SMSMonthToDateSpentUSD"),
            "Label": self.region,
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/SNS",
                    "MetricName": "SMSMonthToDateSpentUSD",
                    "Dimensions": [],
                },
                "Period": self.period,
                "Stat": "Maximum",
                "Unit": "Count",
            },
        }
        return [sms_success_rate_metric, sms_spending_metric]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class SNS(AWSSectionCloudwatch):
    def __init__(self, client: BaseClient, region: str, config: AWSConfig):
        super().__init__(client, region, config)

    @property
    def name(self) -> str:
        return "sns_cloudwatch"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("sns_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        # The metrics of this class are grouped by SNS topic
        metrics = []
        for idx, topic in enumerate(colleague_contents.content):
            for metric_name, stat, unit in [
                ("NumberOfMessagesPublished", "Sum", "Count"),
                ("NumberOfNotificationsDelivered", "Sum", "Count"),
                ("NumberOfNotificationsFailed", "Sum", "Count"),
            ]:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": topic["ItemId"],
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/SNS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "TopicName",
                                    "Value": topic["Name"],
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": stat,
                        "Unit": unit,
                    },
                }
                metrics.append(metric)
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--ECS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___/ ___|                            |
#   |                         |  _|| |   \___ \                            |
#   |                         | |__| |___|___) |                           |
#   |                         |_____\____|____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class StatusEnum(StrEnum):
    active = "ACTIVE"
    provisioning = "PROVISIONING"
    deprovisioning = "DEPROVISIONING"
    failed = "FAILED"
    inactive = "INACTIVE"


class Tag(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    Key: str = Field(..., alias="key")
    Value: str = Field(..., alias="value")


class Cluster(BaseModel):
    clusterArn: str
    clusterName: str
    status: StatusEnum
    tags: Sequence[Tag]
    registeredContainerInstancesCount: int
    activeServicesCount: int
    capacityProviders: Sequence[str]


def get_ecs_cluster_arns(ecs_client: BaseClient) -> Iterable[str]:
    for page in ecs_client.get_paginator("list_clusters").paginate():
        yield from page["clusterArns"]


def get_ecs_clusters(ecs_client: BaseClient, cluster_ids: Sequence[str]) -> Iterable[Cluster]:
    # the ECS.Client API allows fetching up to 100 clusters at once
    for chunk in _chunks(cluster_ids, length=100):
        clusters = ecs_client.describe_clusters(clusters=chunk, include=["TAGS"])  # type: ignore[attr-defined]
        yield from [Cluster(**cluster_data) for cluster_data in clusters["clusters"]]


class ECSLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "ecs_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> tuple[Sequence[object], Sequence[object]]:
        quota_list = list(self._iter_service_quotas("ecs"))
        quota_dicts = [q.model_dump() for q in quota_list]

        cluster_ids = list(get_ecs_cluster_arns(self._client))
        cluster_dicts = [c.model_dump() for c in get_ecs_clusters(self._client, cluster_ids)]

        return quota_dicts, cluster_dicts

    @staticmethod
    def _get_quota_limit(quotas: Sequence[Quota], quota_name: str) -> int:
        for quota in quotas:
            if quota_name == quota.QuotaName:
                return int(quota.Value)

        return AWSECSQuotaDefaults[quota_name]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        quota_dicts, cluster_dicts = raw_content.content
        quotas = [Quota(**c) for c in quota_dicts]
        clusters = [Cluster(**c) for c in cluster_dicts]

        self._add_limit(
            "",
            AWSLimit(
                key="clusters",
                title="Clusters",
                limit=ECSLimits._get_quota_limit(quotas, "Clusters per account"),
                amount=len(clusters),
            ),
            region=self._region,
        )

        for cluster in clusters:
            self._add_limit(
                "",
                AWSLimit(
                    key="capacity_providers",
                    title=f"Capacity providers of {cluster.clusterName}",
                    limit=ECSLimits._get_quota_limit(quotas, "Capacity providers per cluster"),
                    amount=len(cluster.capacityProviders),
                ),
                region=self._region,
            )

            self._add_limit(
                "",
                AWSLimit(
                    key="container_instances",
                    title=f"Container instances of {cluster.clusterName}",
                    limit=ECSLimits._get_quota_limit(quotas, "Container instances per cluster"),
                    amount=cluster.registeredContainerInstancesCount,
                ),
                region=self._region,
            )

            self._add_limit(
                "",
                AWSLimit(
                    key="services",
                    title=f"Services of {cluster.clusterName}",
                    limit=ECSLimits._get_quota_limit(quotas, "Services per cluster"),
                    amount=cluster.activeServicesCount,
                ),
                region=self._region,
            )

        return AWSComputedContent(clusters, raw_content.cache_timestamp)


class ECSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ecs_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["ecs_tags"])

    @property
    def name(self) -> str:
        return "ecs_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ecs_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_cluster_ids(self) -> Iterable[str]:
        if self._names is not None:
            yield from self._names
            return

        yield from get_ecs_cluster_arns(self._client)

    def _fetch_clusters(self, clusters: Sequence[Cluster]) -> Iterable[Cluster]:
        if clusters:
            if self._names is not None:
                yield from (c for c in clusters if c.clusterName in self._names)
            else:
                yield from clusters
        else:
            cluster_ids = list(self._get_cluster_ids())
            yield from get_ecs_clusters(self._client, cluster_ids)

    def _filter_clusters_by_tags(
        self, clusters: Iterable[Cluster]
    ) -> Iterable[Mapping[str, object]]:
        for cluster in clusters:
            for cluster_tag in cluster.tags:
                if self._tags and cluster_tag.model_dump() in self._tags:
                    yield cluster.model_dump()

    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        clusters = self._fetch_clusters(colleague_contents.content)

        if self._tags is not None:
            return list(self._filter_clusters_by_tags(clusters))

        return [c.model_dump() for c in clusters]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        clusters = [Cluster(**c) for c in raw_content.content]
        return AWSComputedContent(clusters, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        clusters = []
        for cluster in computed_content.content:
            data = cluster.model_dump()
            data["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(data.get("tags", []))
            clusters.append(data)
        return [AWSSectionResult("", clusters)]


class ECS(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "ecs"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("ecs_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(
                [cluster.clusterName for cluster in colleague.content],
                colleague.cache_timestamp,
            )
        return AWSColleagueContents([], 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        muv: list[tuple[str, str]] = [
            ("CPUUtilization", "Percent"),
            ("CPUReservation", "Percent"),
            ("MemoryUtilization", "Percent"),
            ("MemoryReservation", "Percent"),
        ]
        metrics: Metrics = []
        for idx, cluster_name in enumerate(colleague_contents.content):
            for metric_name, unit in muv:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": cluster_name,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ECS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "ClusterName",
                                    "Value": cluster_name,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": "Average",
                    },
                }
                if unit:
                    metric["MetricStat"]["Unit"] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


#   .--ElastiCache---------------------------------------------------------.
#   |         _____ _           _   _  ____           _                    |
#   |        | ____| | __ _ ___| |_(_)/ ___|__ _  ___| |__   ___           |
#   |        |  _| | |/ _` / __| __| | |   / _` |/ __| '_ \ / _ \          |
#   |        | |___| | (_| \__ \ |_| | |__| (_| | (__| | | |  __/          |
#   |        |_____|_|\__,_|___/\__|_|\____\__,_|\___|_| |_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


# AWS has different nomenclature for ElastiCache resources in the UI and in
# the API (cluster in the UI is a resource group in The API, node in the UI
# is a cache cluster in the API)
# The following fields are renamed so we can use the UI nomenclature consistently
# in the Checkmk
class ElastiCacheNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    NodeId: str = Field(..., alias="CacheClusterId")
    Engine: str
    ARN: str


class ElastiCacheCluster(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ClusterId: str = Field(..., alias="ReplicationGroupId")
    Status: str
    MemberNodes: Sequence[str] = Field(..., alias="MemberClusters")
    ARN: str


class SubnetGroup(BaseModel):
    CacheSubnetGroupName: str
    ARN: str


class ParameterGroup(BaseModel):
    CacheParameterGroupName: str
    ARN: str


def get_paginated_resources(
    client: BaseClient, paginator_name: str, resource_name: str, resource_type: type[BaseModel]
) -> Iterable[BaseModel]:
    for page in client.get_paginator(paginator_name).paginate():
        for resource_dict in page[resource_name]:
            yield resource_type(**resource_dict)


class ElastiCacheLimits(AWSSectionLimits):
    @property
    def name(self) -> str:
        return "elasticache_limits"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> tuple[
        Sequence[Mapping[str, object]],
        Sequence[Mapping[str, object]],
        Sequence[Mapping[str, object]],
        int,
        int,
    ]:
        quota_list = list(self._iter_service_quotas("elasticache"))
        quota_dicts = [q.model_dump() for q in quota_list]

        cluster_dicts = [
            c.model_dump()
            for c in get_paginated_resources(
                self._client, "describe_replication_groups", "ReplicationGroups", ElastiCacheCluster
            )
        ]

        node_dicts = [
            n.model_dump()
            for n in get_paginated_resources(
                self._client, "describe_cache_clusters", "CacheClusters", ElastiCacheNode
            )
        ]

        subnet_groups = list(
            get_paginated_resources(
                self._client, "describe_cache_subnet_groups", "CacheSubnetGroups", SubnetGroup
            )
        )

        parameter_groups = list(
            get_paginated_resources(
                self._client,
                "describe_cache_parameter_groups",
                "CacheParameterGroups",
                ParameterGroup,
            )
        )

        return (
            quota_dicts,
            cluster_dicts,
            node_dicts,
            len(subnet_groups),
            len(parameter_groups),
        )

    @staticmethod
    def _get_quota_limit(quotas: Sequence[Quota], quota_name: str) -> int:
        for quota in quotas:
            if quota_name == quota.QuotaName:
                return int(quota.Value)
        return AWSElastiCacheQuotaDefaults[quota_name]

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        quotas = [Quota(**q) for q in raw_content.content[0]]
        clusters = [ElastiCacheCluster(**c) for c in raw_content.content[1]]
        nodes = [ElastiCacheNode(**c) for c in raw_content.content[2]]
        subnet_group_count, parameter_group_count = raw_content.content[3:]

        for cluster in clusters:
            self._add_limit(
                "",
                AWSLimit(
                    key="nodes_per_cluster",
                    title=f"Nodes of {cluster.ClusterId}",
                    limit=ElastiCacheLimits._get_quota_limit(
                        quotas, "Nodes per cluster per instance type (Redis cluster mode enabled)"
                    ),
                    amount=len(cluster.MemberNodes),
                ),
                region=self._region,
            )

        self._add_limit(
            "",
            AWSLimit(
                key="nodes",
                title="Nodes",
                limit=ElastiCacheLimits._get_quota_limit(quotas, "Nodes per Region"),
                amount=len(nodes),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                key="subnet_groups",
                title="Subnet groups",
                limit=ElastiCacheLimits._get_quota_limit(quotas, "Subnet groups per Region"),
                amount=subnet_group_count,
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                key="parameter_groups",
                title="Parameter groups",
                limit=ElastiCacheLimits._get_quota_limit(quotas, "Parameter groups per Region"),
                amount=parameter_group_count,
            ),
            region=self._region,
        )

        return AWSComputedContent((clusters, nodes), raw_content.cache_timestamp)


class ElastiCacheSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        tagging_client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._tagging_client = tagging_client
        self._names = self._config.service_config["elasticache_names"]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["elasticache_tags"]
        )

    @property
    def name(self) -> str:
        return "elasticache_summary"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elasticache_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents((), 0.0)

    def _fetch_data(
        self, colleague_content: tuple[Sequence[ElastiCacheCluster], Sequence[ElastiCacheNode]]
    ) -> tuple[Sequence[ElastiCacheCluster], Sequence[ElastiCacheNode]]:
        if colleague_content:
            return colleague_content

        clusters = list(
            get_paginated_resources(
                self._client, "describe_replication_groups", "ReplicationGroups", ElastiCacheCluster
            )
        )

        nodes = list(
            get_paginated_resources(
                self._client, "describe_cache_clusters", "CacheClusters", ElastiCacheNode
            )
        )

        return clusters, nodes

    def _filter_clusters(
        self, clusters: Iterable[ElastiCacheCluster], resource_tags: ResourceTags
    ) -> Iterable[ElastiCacheCluster]:
        if self._names is not None:
            for cluster in clusters:
                if cluster.ClusterId in self._names:
                    yield cluster
            return

        if self._tags is not None:
            matching_arns = filter_resources_matching_tags(resource_tags, self._tags)

            for cluster in clusters:
                if cluster.ARN in matching_arns:
                    yield cluster
            return

        yield from clusters

    def _filter_nodes(
        self, nodes: Sequence[ElastiCacheNode], clusters: Iterable[ElastiCacheCluster]
    ) -> Iterable[Mapping[str, object]]:
        for node in nodes:
            for cluster in clusters:
                if node.NodeId in cluster.MemberNodes:
                    yield node.model_dump()
                    break

    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> tuple[Sequence[Mapping[str, object]], Sequence[Mapping[str, object]]]:
        (colleague_contents,) = args
        clusters, nodes = self._fetch_data(colleague_contents.content)

        resource_tags = fetch_resource_tags_from_types(
            self._tagging_client, ["elasticache:replicationgroup"]
        )
        filtered_clusters = list(self._filter_clusters(clusters, resource_tags))
        filtered_node_dicts = list(self._filter_nodes(nodes, filtered_clusters))

        filtered_cluster_dicts = []
        for cluster in filtered_clusters:
            cluster_dict = cluster.model_dump()
            cluster_dict["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(
                resource_tags.get(cluster.ARN, [])
            )
            filtered_cluster_dicts.append(cluster_dict)

        return filtered_cluster_dicts, filtered_node_dicts

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content[0])]


class ElastiCache(AWSSectionCloudwatch):
    @property
    def name(self) -> str:
        return "elasticache"

    @property
    def cache_interval(self) -> int:
        return 300

    @property
    def granularity(self) -> int:
        return 300

    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elasticache_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(
                [node["NodeId"] for node in colleague.content[1]],
                colleague.cache_timestamp,
            )
        return AWSColleagueContents([], 0.0)

    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        muv: list[tuple[str, str]] = [
            ("CPUUtilization", "Percent"),
            ("EngineCPUUtilization", "Percent"),
            ("BytesUsedForCache", "Bytes"),
            ("DatabaseMemoryUsagePercentage", "Percent"),
            ("Evictions", "Count"),
            ("Reclaimed", "Count"),
            ("MemoryFragmentationRatio", "None"),
            ("CacheHitRate", "Percent"),
            ("CurrConnections", "Count"),
            ("NewConnections", "Count"),
            ("ReplicationLag", "Seconds"),
            ("MasterLinkHealthStatus", "Count"),
        ]
        metrics: Metrics = []

        for idx, node_name in enumerate(colleague_contents.content):
            for metric_name, unit in muv:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": node_name,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ElastiCache",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "CacheClusterId",
                                    "Value": node_name,
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": "Average",
                    },
                }
                if unit:
                    metric["MetricStat"]["Unit"] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


# .
#   .--sections------------------------------------------------------------.
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AWSSections(abc.ABC):
    def __init__(
        self,
        hostname: str,
        session: boto3.session.Session,
        account_id: str,
        debug: bool = False,
        config: botocore.config.Config | None = None,
    ) -> None:
        self._hostname = hostname
        self._session = session
        self._debug = debug
        self._sections: list[AWSSection] = []
        self.config = config
        self.account_id = account_id

    @abc.abstractmethod
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        pass

    def _init_client(self, client_key: str) -> BaseClient:
        try:
            # TODO: The signature of the client() method depends on the literal(!) value of its
            # first argument, so using a plain str here is wrong.
            return self._session.client(client_key, config=self.config)
        except (
            ValueError,
            botocore.exceptions.ClientError,
            botocore.exceptions.UnknownServiceError,
        ) as e:
            # If region name is not valid we get a ValueError
            # but not in all cases, eg.:
            # 1. 'eu-central-' raises a ValueError
            # 2. 'foobar' does not raise a ValueError
            # In the second case we get an exception raised by botocore
            # during we execute an operation, eg. cloudwatch.get_metrics(**kwargs)-> None:
            # - botocore.exceptions.EndpointConnectionError
            logging.info("Invalid region name or client key %s: %s", client_key, e)
            raise

    def run(self, use_cache: bool = True) -> None:
        exceptions: list[AssertionError | Exception] = []
        results: Results = {}

        for section in self._sections:
            try:
                section_result = section.run(use_cache=use_cache)
            except AssertionError as e:
                logging.info(e)
                if self._debug:
                    raise
            except Exception as e:
                logging.info("%s: %s", section.__class__.__name__, e)
                if self._debug:
                    raise
                exceptions.append(e)
            else:
                results.setdefault(
                    (section.name, section_result.cache_timestamp, section.cache_interval),
                    section_result.results,
                )

        self._write_exceptions(exceptions)
        self._write_host_labels(results)
        self._write_section_results(results)

    def _collect_static_host_labels(self) -> Mapping[str, str]:
        """Labels every host will be labelled with regardless of type"""
        host_labels = {"cmk/aws/account": self.account_id}
        return host_labels

    def _is_piggyback_host_result(self, section_result: AWSSectionResult) -> bool:
        return section_result.piggyback_hostname not in {None, "", self._hostname}

    def _collect_piggyback_host_labels(
        self, results: Results, static_labels: Mapping[str, str]
    ) -> Mapping[str, Mapping[str, str]]:
        """Labels dependent on the type of piggyback host"""
        host_labels: dict[str, dict[str, str]] = defaultdict(lambda: {**static_labels})
        for result in results.values():
            for row in result:
                if self._is_piggyback_host_result(row) and row.piggyback_host_labels:
                    host_labels[str(row.piggyback_hostname)].update(row.piggyback_host_labels)
        return host_labels

    def _write_labels_section(self, host_labels: Mapping[str, str]) -> None:
        with SectionWriter("labels") as w:
            w.append(json.dumps(host_labels))

    def _write_host_labels(self, results: Results) -> None:
        static_host_labels = self._collect_static_host_labels()
        self._write_labels_section(static_host_labels)

        piggyback_host_labels = self._collect_piggyback_host_labels(results, static_host_labels)
        for hostname, host_labels in piggyback_host_labels.items():
            with ConditionalPiggybackSection(hostname):
                self._write_labels_section(host_labels)

    def _safe_exception(self, exception: Exception) -> str:
        """
        Secure proper exception output.
        boto3 sometimes throws unpropper exceptions without a 'message' parameter.
        TODO: Avoid using aws_exception-section
        """
        if hasattr(exception, "message"):
            return exception.message

        return repr(exception)

    def _write_exceptions(self, exceptions: Sequence) -> None:
        sys.stdout.write("<<<aws_exceptions>>>\n")

        if exceptions:
            out = "\n".join([self._safe_exception(e) for e in exceptions])
        else:
            out = "No exceptions"
        sys.stdout.write(f"{self.__class__.__name__}: {out}\n")

    def _write_section_results(self, results: Results) -> None:
        if not results:
            logging.info("%s: No results or cached data", self.__class__.__name__)
            return

        for (section_name, cache_timestamp, section_interval), result in results.items():
            if not result:
                logging.info("%s: No results", section_name)
                continue

            if not isinstance(result, list):
                logging.info(
                    "%s: Section result must be of type 'list' containing 'AWSSectionResults'",
                    section_name,
                )
                continue

            cached_suffix = ""
            if section_interval > 60:
                cached_suffix = f":cached({int(cache_timestamp)},{int(section_interval + 60)})"

            if any(r.content for r in result):
                self._write_section_result(section_name, cached_suffix, result)

    def _write_section_result(
        self, section_name: str, cached_suffix: str, result: Sequence[AWSSectionResult]
    ) -> None:
        if section_name.endswith("labels"):
            section_header = f"<<<{section_name}:sep(0){cached_suffix}>>>\n"
        else:
            section_header = f"<<<aws_{section_name}{cached_suffix}>>>\n"

        for row in result:
            write_piggyback_header = self._is_piggyback_host_result(row)
            if write_piggyback_header:
                sys.stdout.write("<<<<%s>>>>\n" % str(row.piggyback_hostname))
            sys.stdout.write(section_header)
            sys.stdout.write("%s\n" % json.dumps(row.content, default=datetime_serializer))
            if write_piggyback_header:
                sys.stdout.write("<<<<>>>>\n")


class AWSSectionsUSEast(AWSSections):
    """
    Some clients like CostExplorer only work with US East region:
    https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html
    US East is the AWS Standard region.
    """

    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        distributor = ResultDistributor()

        if "ce" in services:
            ce_client = self._init_client("ce")
            self._sections.append(CostsAndUsage(ce_client, region, config))
            self._sections.append(ReservationUtilization(ce_client, region, config))

        cloudwatch_client = self._init_client("cloudwatch")
        tagging_client = self._init_client("resourcegroupstaggingapi")
        if "wafv2" in services and config.service_config["wafv2_cloudfront"]:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "CLOUDFRONT", distributor=distributor
            )
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "CLOUDFRONT", distributor=distributor
            )
            distributor.add(wafv2_limits.name, wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, False)
            distributor.add(wafv2_summary.name, wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "route53" in services:
            route53_client = self._init_client("route53")
            route53_health_checks, route53_cloudwatch = _create_route53_sections(
                route53_client, cloudwatch_client, region, config, distributor
            )
            self._sections.append(route53_health_checks)
            self._sections.append(route53_cloudwatch)

        if "cloudfront" in services:
            cloudfront_client = self._init_client("cloudfront")
            cloudfront_summary = CloudFrontSummary(
                cloudfront_client, tagging_client, region, config, distributor
            )
            cloudfront = CloudFront(
                cloudwatch_client,
                region,
                config,
                config.service_config["cloudfront_host_assignment"],
            )
            distributor.add(cloudfront_summary.name, cloudfront)
            self._sections.append(cloudfront_summary)
            self._sections.append(cloudfront)


def _create_lamdba_sections(
    lambda_client: BaseClient,
    cloudwatch_client: BaseClient,
    cloudwatch_logs_client: BaseClient,
    region: str,
    config: AWSConfig,
    distributor: ResultDistributor,
) -> tuple[
    LambdaRegionLimits,
    LambdaSummary,
    LambdaProvisionedConcurrency,
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
]:
    lambda_limits = LambdaRegionLimits(lambda_client, region, config, distributor=distributor)
    lambda_summary = LambdaSummary(
        lambda_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_limits.name, lambda_summary)
    lambda_provisioned_concurrency_configuration = LambdaProvisionedConcurrency(
        lambda_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_summary.name, lambda_provisioned_concurrency_configuration)
    lambda_cloudwatch = LambdaCloudwatch(cloudwatch_client, region, config)
    distributor.add(lambda_provisioned_concurrency_configuration.name, lambda_cloudwatch)
    lambda_cloudwatch_insights = LambdaCloudwatchInsights(
        cloudwatch_logs_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_provisioned_concurrency_configuration.name, lambda_cloudwatch_insights)

    return (
        lambda_limits,
        lambda_summary,
        lambda_provisioned_concurrency_configuration,
        lambda_cloudwatch,
        lambda_cloudwatch_insights,
    )


def _create_route53_sections(
    route53_client: BaseClient,
    cloudwatch_client: BaseClient,
    region: str,
    config: AWSConfig,
    distributor: ResultDistributor,
) -> tuple[Route53HealthChecks, Route53Cloudwatch]:
    route53_health_checks = Route53HealthChecks(route53_client, region, config, distributor)
    route53_cloudwatch = Route53Cloudwatch(cloudwatch_client, region, config, distributor=None)
    distributor.add(route53_health_checks.name, route53_cloudwatch)
    return route53_health_checks, route53_cloudwatch


class AWSSectionsGeneric(AWSSections):
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        distributor = ResultDistributor()

        cloudwatch_client = self._init_client("cloudwatch")
        tagging_client = self._init_client("resourcegroupstaggingapi")
        ec2_client = self._init_client("ec2")
        ebs_summary = EBSSummary(ec2_client, region, config, distributor)

        if "ec2" in services:
            ec2_summary = EC2Summary(ec2_client, region, config, distributor)
            ec2_labels = EC2Labels(ec2_client, region, config)
            ec2_security_groups = EC2SecurityGroups(ec2_client, region, config)
            ec2 = EC2(cloudwatch_client, region, config)
            distributor.add("ec2_limits", ec2_summary)
            distributor.add(ec2_summary.name, ec2_labels)
            distributor.add(ec2_summary.name, ec2_security_groups)
            distributor.add(ec2_summary.name, ec2)
            distributor.add(ec2_summary.name, ebs_summary)
            if config.service_config.get("ec2_limits"):
                self._sections.append(
                    EC2Limits(
                        ec2_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )
            self._sections.append(ec2_summary)
            self._sections.append(ec2_labels)
            self._sections.append(ec2_security_groups)
            self._sections.append(ec2)

        if "ebs" in services:
            ebs = EBS(cloudwatch_client, region, config)
            distributor.add("ebs_limits", ebs_summary)
            distributor.add(ebs_summary.name, ebs)
            if config.service_config.get("ebs_limits"):
                self._sections.append(EBSLimits(ec2_client, region, config, distributor))
            self._sections.append(ebs_summary)
            self._sections.append(ebs)

        if "elb" in services:
            elb_client = self._init_client("elb")
            elb_labels = ELBLabelsGeneric(elb_client, region, config, resource="elb")
            elb_health = ELBHealth(elb_client, region, config)
            elb = ELB(cloudwatch_client, region, config)
            elb_summary = ELBSummaryGeneric(elb_client, region, config, distributor, resource="elb")
            distributor.add("elb_limits", elb_summary)
            distributor.add(elb_summary.name, elb_labels)
            distributor.add(elb_summary.name, elb_health)
            distributor.add(elb_summary.name, elb)
            if config.service_config.get("elb_limits"):
                self._sections.append(ELBLimits(elb_client, region, config, distributor))
            self._sections.append(elb_summary)
            self._sections.append(elb_labels)
            self._sections.append(elb_health)
            self._sections.append(elb)

        if "elbv2" in services:
            elbv2_client = self._init_client("elbv2")
            elbv2_limits = ELBv2Limits(elbv2_client, region, config, distributor)
            elbv2_summary = ELBSummaryGeneric(
                elbv2_client, region, config, distributor, resource="elbv2"
            )
            elbv2_labels = ELBLabelsGeneric(elbv2_client, region, config, resource="elbv2")
            elbv2_target_groups = ELBv2TargetGroups(elbv2_client, region, config)
            elbv2_application = ELBv2Application(cloudwatch_client, region, config)
            elbv2_application_target_groups_http = ELBv2ApplicationTargetGroupsHTTP(
                cloudwatch_client, region, config
            )
            elbv2_application_target_groups_lambda = ELBv2ApplicationTargetGroupsLambda(
                cloudwatch_client, region, config
            )
            elbv2_network = ELBv2Network(cloudwatch_client, region, config)
            distributor.add(elbv2_limits.name, elbv2_summary)
            distributor.add(elbv2_summary.name, elbv2_labels)
            distributor.add(elbv2_summary.name, elbv2_target_groups)
            distributor.add(elbv2_summary.name, elbv2_application)
            distributor.add(elbv2_summary.name, elbv2_application_target_groups_http)
            distributor.add(elbv2_summary.name, elbv2_application_target_groups_lambda)
            distributor.add(elbv2_summary.name, elbv2_network)
            if config.service_config.get("elbv2_limits"):
                self._sections.append(elbv2_limits)
            self._sections.append(elbv2_summary)
            self._sections.append(elbv2_labels)
            self._sections.append(elbv2_target_groups)
            self._sections.append(elbv2_application)
            self._sections.append(elbv2_application_target_groups_http)
            self._sections.append(elbv2_application_target_groups_lambda)
            self._sections.append(elbv2_network)

        if "s3" in services:
            # S3 is special because there are no per-region limits, but only a global per-account limit.
            # The list of buckets can be queried from any region, however, the metrics for the
            # individual buckets must be queried from the region the bucket resides in. Therefore, we
            # only want to run S3Limits once, namely for the first region (does not matter which region
            # that is). The results will then be distributed to the S3Summary objects across all regions
            # using the special distributor for S3 limits.
            s3_client = self._init_client("s3")
            if s3_limits_distributor.is_empty():
                s3_limits: S3Limits | None = S3Limits(
                    s3_client, region, config, s3_limits_distributor
                )
            else:
                s3_limits = None
            s3_summary = S3Summary(s3_client, region, config, distributor)

            s3_limits_distributor.add("s3_limits", s3_summary)
            s3 = S3(cloudwatch_client, region, config)
            distributor.add(s3_summary.name, s3)
            s3_requests = S3Requests(cloudwatch_client, region, config)
            distributor.add(s3_summary.name, s3_requests)
            if config.service_config.get("s3_limits") and s3_limits:
                self._sections.append(s3_limits)
            self._sections.append(s3_summary)
            self._sections.append(s3)
            if config.service_config["s3_requests"]:
                self._sections.append(s3_requests)

        if "glacier" in services:
            glacier_client = self._init_client("glacier")
            glacier_limits = GlacierLimits(glacier_client, region, config, distributor)
            glacier_summary = Glacier(glacier_client, region, config)
            distributor.add(glacier_limits.name, glacier_summary)
            if config.service_config.get("glacier_limits"):
                self._sections.append(glacier_limits)
            self._sections.append(glacier_summary)

        if "rds" in services:
            rds_client = self._init_client("rds")
            rds_summary = RDSSummary(rds_client, region, config, distributor)
            rds_limits = RDSLimits(rds_client, region, config)
            rds = RDS(cloudwatch_client, region, config)
            distributor.add(rds_summary.name, rds)
            if config.service_config.get("rds_limits"):
                self._sections.append(rds_limits)
            self._sections.append(rds_summary)
            self._sections.append(rds)

        if "cloudwatch_alarms" in services:
            cloudwatch_alarms = CloudwatchAlarms(cloudwatch_client, region, config)
            cloudwatch_alarms_limits = CloudwatchAlarmsLimits(
                cloudwatch_client, region, config, distributor
            )
            distributor.add(cloudwatch_alarms_limits.name, cloudwatch_alarms)
            if config.service_config.get("cloudwatch_alarms_limits"):
                self._sections.append(cloudwatch_alarms_limits)
            if "cloudwatch_alarms" in config.service_config:
                self._sections.append(cloudwatch_alarms)

        if "dynamodb" in services:
            dynamodb_client = self._init_client("dynamodb")
            dynamodb = DynamoDB(dynamodb_client, region, config)
            dynamodb_labels = DynamoDBLabelsGeneric(
                dynamodb_client, region, config, resource="dynamodb"
            )
            dynamodb_limits = DynamoDBLimits(dynamodb_client, region, config, distributor)
            dynamodb_summary = DynamoDBSummary(dynamodb_client, region, config, distributor)
            dynamodb_table = DynamoDBTable(cloudwatch_client, region, config)
            distributor.add(dynamodb_limits.name, dynamodb_summary)
            distributor.add(dynamodb_summary.name, dynamodb_labels)
            distributor.add(dynamodb_summary.name, dynamodb)
            distributor.add(dynamodb_summary.name, dynamodb_table)
            if config.service_config.get("dynamodb_limits"):
                self._sections.append(dynamodb_limits)
            self._sections.append(dynamodb_summary)
            self._sections.append(dynamodb_labels)
            self._sections.append(dynamodb)
            self._sections.append(dynamodb_table)

        if "wafv2" in services:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "REGIONAL", distributor=distributor
            )
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "REGIONAL", distributor=distributor
            )
            distributor.add(wafv2_limits.name, wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, True)
            distributor.add(wafv2_summary.name, wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "lambda" in services:
            (
                lambda_limits,
                lambda_summary,
                lambda_provisioned_concurrency_configuration,
                lambda_cloudwatch,
                lambda_cloudwatch_insights,
            ) = _create_lamdba_sections(
                self._init_client("lambda"),
                cloudwatch_client,
                self._init_client("logs"),
                region,
                config,
                distributor,
            )
            if config.service_config.get("lambda_limits"):
                self._sections.append(lambda_limits)
            self._sections.append(lambda_summary)
            self._sections.append(lambda_provisioned_concurrency_configuration)
            self._sections.append(lambda_cloudwatch)
            self._sections.append(lambda_cloudwatch_insights)

        if "sns" in services:
            sns_client = self._init_client("sns")
            sns_topics_fetcher = SNSTopicsFetcher(sns_client, tagging_client, region, config)
            sns_summary = SNSSummary(
                sns_client, region, config, sns_topics_fetcher, distributor=distributor
            )
            sns_cloudwatch = SNS(cloudwatch_client, region, config)
            distributor.add(sns_summary.name, sns_cloudwatch)
            sns_sms_cloudwatch = SNSSMS(cloudwatch_client, region, config)
            if config.service_config.get("sns_limits"):
                sns_limits = SNSLimits(
                    sns_client, region, config, sns_topics_fetcher, distributor=distributor
                )
                distributor.add(sns_limits.name, sns_summary)
                distributor.add(sns_limits.name, sns_cloudwatch)
                self._sections.append(sns_limits)
            # sns_cloudwatch section should always be after sns_limits because it gets the data from
            # there through the distributor
            self._sections.append(sns_summary)
            self._sections.append(sns_cloudwatch)
            self._sections.append(sns_sms_cloudwatch)

        if "ecs" in services:
            ecs_client = self._init_client("ecs")
            if config.service_config.get("ecs_limits"):
                self._sections.append(
                    ECSLimits(
                        ecs_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )

            ecs_summary = ECSSummary(ecs_client, region, config, distributor)
            distributor.add("ecs_limits", ecs_summary)
            self._sections.append(ecs_summary)

            ecs = ECS(cloudwatch_client, region, config)
            distributor.add("ecs_summary", ecs)
            self._sections.append(ecs)

        if "elasticache" in services:
            elasticache_client = self._init_client("elasticache")
            if config.service_config.get("elasticache_limits"):
                self._sections.append(
                    ElastiCacheLimits(
                        elasticache_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )

            elasticache_summary = ElastiCacheSummary(
                elasticache_client, tagging_client, region, config, distributor
            )
            distributor.add("elasticache_limits", elasticache_summary)
            self._sections.append(elasticache_summary)

            elasticache = ElastiCache(cloudwatch_client, region, config)
            distributor.add("elasticache_summary", elasticache)
            self._sections.append(elasticache)


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AWSServiceAttributes(NamedTuple):
    key: str
    title: str
    global_service: bool
    filter_by_names: bool
    filter_by_tags: bool
    limits: bool


AWSServices = [
    AWSServiceAttributes(
        key="ce",
        title="Costs and usage",
        global_service=True,
        filter_by_names=False,
        filter_by_tags=False,
        limits=False,
    ),
    AWSServiceAttributes(
        key="ec2",
        title="Elastic Compute Cloud (EC2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="ebs",
        title="Elastic Block Storage (EBS)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="s3",
        title="Simple Storage Service (S3)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="glacier",
        title="Simple Storage Service Glacier (Glacier)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elb",
        title="Classic Load Balancing (ELB)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elbv2",
        title="Application and Network Load Balancing (ELBv2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="rds",
        title="Relational Database Service (RDS)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="cloudwatch_alarms",
        title="CloudWatch Alarms",
        global_service=False,
        filter_by_names=False,
        filter_by_tags=False,
        limits=True,
    ),
    AWSServiceAttributes(
        key="dynamodb",
        title="DynamoDB",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="wafv2",
        title="Web Application Firewall (WAFV2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="lambda",
        title="Lambda",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="route53",
        title="Route53",
        global_service=True,
        filter_by_names=True,
        filter_by_tags=True,
        limits=False,
    ),
    AWSServiceAttributes(
        key="sns",
        title="SNS",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="cloudfront",
        title="CloudFront",
        global_service=True,
        filter_by_names=True,
        filter_by_tags=True,
        limits=False,
    ),
    AWSServiceAttributes(
        key="ecs",
        title="ECS",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elasticache",
        title="ElastiCache",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
]


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log messages from AWS library 'boto3' and 'botocore'.",
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_post_data_parameters=[("client_secret", "****")]),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Execute all sections, do not rely on cached data. Cached data will not be overwritten.",
    )
    parser.add_argument(
        "--access-key-id",
        required=False,
        help="The access key ID for your AWS account",
    )
    group_secret_access_key = parser.add_mutually_exclusive_group(required=False)
    group_secret_access_key.add_argument(
        "--secret-access-key-reference",
        help="Password store reference to the secret access key for your AWS account.",
    )
    group_secret_access_key.add_argument(
        "--secret-access-key",
        help="The secret access key for your AWS account.",
    )
    parser.add_argument("--proxy-host", help="The address of the proxy server")
    parser.add_argument("--proxy-port", help="The port of the proxy server")
    parser.add_argument("--proxy-user", help="The username for authentication of the proxy server")
    group_proxy_password = parser.add_mutually_exclusive_group()
    group_proxy_password.add_argument(
        "--proxy-password-reference",
        help="Password store reference to the password for authentication of the proxy server",
    )
    group_proxy_password.add_argument(
        "--proxy-password",
        help="The password for authentication of the proxy server",
    )
    parser.add_argument(
        "--global-service-region",
        help="Set this to your region when you are in 'us-gov-*' or 'cn-*' regions.",
        default="us-east-1",
    )
    parser.add_argument(
        "--assume-role",
        action="store_true",
        help="Use STS AssumeRole to assume a different IAM role",
    )
    parser.add_argument("--role-arn", help="The ARN of the IAM role to assume")
    parser.add_argument(
        "--external-id", help="Unique identifier to assume a role in another account"
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        help="Regions to use:\n%s" % "\n".join(["%-15s %s" % e for e in AWSRegions]),
    )
    parser.add_argument(
        "--global-services",
        nargs="+",
        help="Global services to monitor:\n%s"
        % "\n".join(["%-15s %s" % (e.key, e.title) for e in AWSServices if e.global_service]),
    )
    parser.add_argument(
        "--services",
        nargs="+",
        help="Services per region to monitor:\n%s"
        % "\n".join(["%-15s %s" % (e.key, e.title) for e in AWSServices if not e.global_service]),
    )
    parser.add_argument(
        "--s3-requests",
        action="store_true",
        help="You have to enable requests metrics in AWS/S3 console. This is a paid feature.",
    )
    parser.add_argument("--cloudwatch-alarms", nargs="*")
    parser.add_argument("--overall-tag-key", nargs=1, action="append", help="Overall tag key")
    parser.add_argument(
        "--overall-tag-values", nargs="+", action="append", help="Overall tag values"
    )
    parser.add_argument(
        "--wafv2-cloudfront",
        action="store_true",
        help="Also monitor global WAFs in front of CloudFront resources.",
    )
    parser.add_argument(
        "--cloudfront-host-assignment",
        help="Assign CloudFront services to the AWS host or to the origin domain host",
    )
    parser.add_argument("--hostname", required=True)
    parser.add_argument(
        "--piggyback-naming-convention",
        type=NamingConvention,
        required=True,
        help="For each running EC2 instance a piggyback host is created. This option changes the "
        "naming of these hosts. Note, that not every host name is pingable. Moreover, "
        "changes in the piggyback name will cause the piggyback host to be reset. "
        "If you choose `ip_region_instance`, then the name includes the private IP "
        "address, the region and the instance ID: {Private IPv4 address}-{region}-{Instance ID}. ",
    )

    group_import_tags = parser.add_mutually_exclusive_group()
    group_import_tags.add_argument(
        "--ignore-all-tags",
        action="store_const",
        const=TagsImportPatternOption.ignore_all,
        dest="tag_key_pattern",
        help="By default, all AWS tags are written to the agent output, validated to meet the "
        "Checkmk label requirements and added as host labels to their respective piggyback host "
        "and/or as service labels to the respective service using the syntax "
        "'cmk/aws/tag/{key}:{value}'. With this option you can disable the import of AWS "
        "tags.",
    )
    group_import_tags.add_argument(
        "--import-matching-tags-as-labels",
        dest="tag_key_pattern",
        help="You can restrict the imported tags by specifying a pattern which the agent searches "
        "for in the key of the tag.",
    )
    group_import_tags.set_defaults(tag_key_pattern=TagsImportPatternOption.import_all)

    for service in AWSServices:
        if service.filter_by_names:
            parser.add_argument(
                "--%s-names" % service.key, nargs="+", help="Names for %s" % service.title
            )
        if service.filter_by_tags:
            parser.add_argument(
                "--%s-tag-key" % service.key,
                nargs=1,
                action="append",
                help="Tag key for %s" % service.title,
            )
            parser.add_argument(
                "--%s-tag-values" % service.key,
                nargs="+",
                action="append",
                help="Tag values for %s" % service.title,
            )
        if service.limits:
            parser.add_argument(
                "--%s-limits" % service.key,
                action="store_true",
                help="Monitor limits for %s" % service.title,
            )

    parser.add_argument(
        "--connection-test",
        action="store_true",
        help="Run a connection test. No further agent code is executed.",
    )

    return parser.parse_args(argv)


def _setup_logging(opt_debug: bool, opt_verbose: bool) -> None:
    logger = logging.getLogger()
    logger.disabled = True
    fmt = "%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s"
    lvl = logging.INFO
    if opt_verbose:
        logger.disabled = False
        lvl = logging.DEBUG
    elif opt_debug:
        logger.disabled = False
    logging.basicConfig(level=lvl, format=fmt)


def _create_anonymous_session(
    region: str,
    config: botocore.config.Config | None,
) -> boto3.session.Session:
    try:
        # According to the documentation of AWS botocore this could snippet should be necessary for anonymous sessions.
        # However this does not work and has to be left out (a reported bug on github).
        # Leave it here for potential future bugfix of the AWS botocore.
        # https://github.com/boto/botocore/issues/1395
        # https://github.com/boto/botocore/issues/2442
        # When necessary return -> tuple[boto3.session.Session, botocore.config.Config | None]:
        # ---------------------------------
        # if config is None:
        #     config = botocore.config.Config(signature_version=botocore.UNSIGNED)
        # else:
        #     config.signature_version = botocore.UNSIGNED  # type: ignore[attr-defined]

        return boto3.session.Session(
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _create_session(
    access_key_id: str | None,
    secret_access_key: str | None,
    region: str,
    config: botocore.config.Config | None,
) -> boto3.session.Session:
    if access_key_id is None or secret_access_key is None:
        return _create_anonymous_session(region=region, config=config)

    try:
        return boto3.session.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _sts_assume_role(
    access_key_id: str | None,
    secret_access_key: str | None,
    role_arn: str,
    external_id: str,
    region: str,
    config: botocore.config.Config | None,
) -> boto3.session.Session:
    """
    Returns a session using a set of temporary security credentials that
    you can use to access AWS resources from another account.
    :param access_key_id: AWS credentials
    :param secret_access_key: AWS credentials
    :param role_arn: The Amazon Resource Name (ARN) of the role to assume
    :param region: AWS region
    :param external_id: Unique identifier to assume a role in another account (optional)
    :return: AWS session
    """
    try:
        session = _create_session(access_key_id, secret_access_key, region, config)

        sts_client = session.client("sts", config=config)

        if external_id:
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName="AssumeRoleSession", ExternalId=external_id
            )
        else:
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName="AssumeRoleSession"
            )

        credentials = assumed_role_object["Credentials"]
        return boto3.session.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _sanitize_aws_services_params(
    g_aws_services: Sequence[str],
    r_aws_services: Sequence[str],
    r_and_g_aws_services: tuple[str] | tuple[()] = (),
) -> tuple[Sequence[str], Sequence[str]]:
    """
    Sort service keys into global and regional services by checking
    the service configuration of AWSServices.
    This abstracts the AWS structure from the GUI configuration.
    :param g_aws_services: all services in --global-services
    :param r_aws_services: all services in --services
    :param r_and_g_aws_services: services in --services which should also be run globally, e.g.
                                 WAFV2, which has regional and global firewalls; the regional ones
                                 can only be accessed from the corresponding region, the global
                                 ones only from us-east-1
    :return: two lists of global and regional services
    """
    aws_service_keys: set[str] = set()
    if g_aws_services is not None:
        aws_service_keys = aws_service_keys.union(g_aws_services)

    if r_aws_services is not None:
        aws_service_keys = aws_service_keys.union(r_aws_services)

    aws_services_map = {e.key: e for e in AWSServices}
    global_services = []
    regional_services = []
    for service_key in aws_service_keys:
        service_attrs = aws_services_map.get(service_key)
        if service_attrs is None:
            continue
        if service_attrs.global_service:
            global_services.append(service_key)
        else:
            regional_services.append(service_key)
            if service_key in r_and_g_aws_services:
                global_services.append(service_key)
    return global_services, regional_services


def _proxy_address(
    server_address: str,
    port: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    address = server_address
    authentication = ""
    if port:
        address += f":{port}"
    if username and password:
        authentication = f"{username}:{password}@"
    return f"{authentication}{address}"


def _get_proxy(args: argparse.Namespace) -> botocore.config.Config | None:
    if args.proxy_host:
        if args.proxy_password:
            proxy_password = args.proxy_password
        elif args.proxy_password_reference:
            pw_id, pw_file = args.proxy_password_reference.split(":", 1)
            proxy_password = password_store.lookup(Path(pw_file), pw_id)
        else:
            proxy_password = None
        return botocore.config.Config(
            proxies={
                "https": _proxy_address(
                    args.proxy_host,
                    args.proxy_port,
                    args.proxy_user,
                    proxy_password,
                )
            }
        )
    return None


def _configure_aws(args: Args) -> AWSConfig:
    aws_config = AWSConfig(
        args.hostname,
        args,
        (args.overall_tag_key, args.overall_tag_values),
        args.piggyback_naming_convention,
        args.tag_key_pattern,
    )
    for service_key, service_names, service_tags, service_limits in [
        ("ec2", args.ec2_names, (args.ec2_tag_key, args.ec2_tag_values), args.ec2_limits),
        ("ebs", args.ebs_names, (args.ebs_tag_key, args.ebs_tag_values), args.ebs_limits),
        ("s3", args.s3_names, (args.s3_tag_key, args.s3_tag_values), args.s3_limits),
        (
            "glacier",
            args.glacier_names,
            (args.glacier_tag_key, args.glacier_tag_values),
            args.glacier_limits,
        ),
        ("elb", args.elb_names, (args.elb_tag_key, args.elb_tag_values), args.elb_limits),
        ("elbv2", args.elbv2_names, (args.elbv2_tag_key, args.elbv2_tag_values), args.elbv2_limits),
        ("rds", args.rds_names, (args.rds_tag_key, args.rds_tag_values), args.rds_limits),
        (
            "dynamodb",
            args.dynamodb_names,
            (args.dynamodb_tag_key, args.dynamodb_tag_values),
            args.dynamodb_limits,
        ),
        ("wafv2", args.wafv2_names, (args.wafv2_tag_key, args.wafv2_tag_values), args.wafv2_limits),
        (
            "lambda",
            args.lambda_names,
            (args.lambda_tag_key, args.lambda_tag_values),
            args.lambda_limits,
        ),
        ("route53", args.route53_names, (args.route53_tag_key, args.route53_tag_values), None),
        ("sns", args.sns_names, (args.sns_tag_key, args.sns_tag_values), args.sns_limits),
        (
            "cloudfront",
            args.cloudfront_names,
            (args.cloudfront_tag_key, args.cloudfront_tag_values),
            None,
        ),
        ("ecs", args.ecs_names, (args.ecs_tag_key, args.ecs_tag_values), args.ecs_limits),
        (
            "elasticache",
            args.elasticache_names,
            (args.elasticache_tag_key, args.elasticache_tag_values),
            args.elasticache_limits,
        ),
    ]:
        aws_config.add_single_service_config("%s_names" % service_key, service_names)
        aws_config.add_service_tags("%s_tags" % service_key, service_tags)
        aws_config.add_single_service_config("%s_limits" % service_key, service_limits)

    for arg in [
        "s3_requests",
        "cloudwatch_alarms_limits",
        "cloudwatch_alarms",
        "wafv2_cloudfront",
        "cloudfront_host_assignment",
    ]:
        aws_config.add_single_service_config(arg, getattr(args, arg))

    return aws_config


def _create_session_from_args(
    args: Args, region: str, config: botocore.config.Config | None
) -> boto3.session.Session:
    secret_access_key = None
    if args.secret_access_key:
        secret_access_key = args.secret_access_key
    elif args.secret_access_key_reference:
        pw_id, pw_file = args.secret_access_key_reference.split(":", 1)
        secret_access_key = password_store.lookup(Path(pw_file), pw_id)

    if args.assume_role:
        return _sts_assume_role(
            args.access_key_id,
            secret_access_key,
            args.role_arn,
            args.external_id,
            region,
            config,
        )

    return _create_session(args.access_key_id, secret_access_key, region, config=config)


def _get_account_id(args: Args, config: botocore.config.Config | None) -> str:
    session = _create_session_from_args(args, args.global_service_region, config)
    try:
        account_id = session.client("sts", config=config).get_caller_identity()["Account"]
    except (
        botocore.exceptions.ClientError,
        botocore.exceptions.NoCredentialsError,
        botocore.exceptions.ProxyConnectionError,
    ) as e:
        raise AwsAccessError(e)
    return account_id


def _test_connection(args: Args, proxy_config: botocore.config.Config | None) -> int:
    try:
        _get_account_id(args, proxy_config)
    except AwsAccessError as ae:
        error_msg = f"Connection failed with: {ae}\n"
        sys.stderr.write(error_msg)
        return 2
    return 0


def agent_aws_main(args: Args) -> int:
    _setup_logging(args.debug, args.verbose)

    proxy_config = _get_proxy(args)

    if args.connection_test:
        return _test_connection(args, proxy_config)

    try:
        account_id = _get_account_id(args, proxy_config)
    except AwsAccessError as ae:
        # can not access AWS, retreat
        sys.stdout.write("<<<aws_exceptions>>>\n")
        sys.stdout.write("Exception: %s\n" % ae)
        return 0

    aws_config = _configure_aws(args)

    global_services, regional_services = _sanitize_aws_services_params(
        args.global_services, args.services, r_and_g_aws_services=("wafv2",)
    )

    use_cache = aws_config.is_up_to_date() and not args.no_cache

    # Special distributor for S3 limits which distributes results across different regions
    s3_limits_distributor = ResultDistributorS3Limits()

    if regional_services and not args.regions:
        logging.error(
            (
                "You have to specify a region for the services: %s."
                " Otherwise data for these services cannot be fetched."
            ),
            ", ".join(regional_services),
        )

    has_exceptions = False
    for aws_services, aws_regions, aws_sections in [
        (global_services, [args.global_service_region], AWSSectionsUSEast),
        (regional_services, args.regions, AWSSectionsGeneric),
    ]:
        if not aws_services or not aws_regions:
            continue

        for region in aws_regions:
            try:
                session = _create_session_from_args(args, region, proxy_config)
                sections = aws_sections(
                    args.hostname, session, account_id, debug=args.debug, config=proxy_config
                )
                sections.init_sections(aws_services, region, aws_config, s3_limits_distributor)
                sections.run(use_cache=use_cache)
            except AwsAccessError as ae:
                # can not access AWS, retreat
                sys.stdout.write("<<<aws_exceptions>>>\n")
                sys.stdout.write("Exception: %s\n" % ae)
                return 0
            except AssertionError:
                if args.debug:
                    raise
            except Exception as e:
                logging.info(e)
                has_exceptions = True
                if args.debug:
                    raise

    return 1 if has_exceptions else 0


class AwsAccessError(MKException):
    pass


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_aws_main)


if __name__ == "__main__":
    sys.exit(main())
