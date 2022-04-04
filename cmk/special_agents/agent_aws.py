#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Amazon web services (AWS) with Check_MK.
"""

import abc
import argparse
import errno
import hashlib
import itertools
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
)

import boto3  # type: ignore[import]
import botocore  # type: ignore[import]

import cmk.utils.password_store
import cmk.utils.store as store
from cmk.utils.aws_constants import (
    AWSEC2InstFamilies,
    AWSEC2InstTypes,
    AWSEC2LimitsDefault,
    AWSEC2LimitsSpecial,
    AWSRegions,
)
from cmk.utils.exceptions import MKException
from cmk.utils.paths import tmp_dir

from cmk.special_agents.utils import (
    DataCache,
    datetime_serializer,
    get_seconds_since_midnight,
    vcrtrace,
)

NOW = datetime.now()

# NOTE: Quite a few of the type annotations below are just "educated guesses"
# and may be wrong, but at least they make mypy happy for now. Nevertheless, we
# really need more type annotations to comprehend the dict-o-mania below...

AWSStrings = Union[bytes, str]

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

# EC2Limits
# |
# '-- EC2Summary
#     |
#     |-- EC2Labels
#     |
#     |-- EC2SecurityGroups
#     |
#     '-- EC2

# S3Limits
# |
# '-- S3Summary
#     |
#     |-- S3
#     |
#     '-- S3Requests

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

# EBSLimits,EC2Summary
# |
# '-- EBSSummary
#     |
#     '-- EBS

# RDSLimits

# RDSSummary
# |
# '-- RDS

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


class AWSConfig:
    def __init__(self, hostname, sys_argv, overall_tags):
        self.hostname = hostname
        self._overall_tags = self._prepare_tags(overall_tags)
        self.service_config = {}
        self._config_hash_file = AWSCacheFilePath / ("%s.config_hash" % hostname)
        self._current_config_hash = self._compute_config_hash(sys_argv)

    def add_service_tags(self, tags_key, tags):
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

    def _prepare_tags(self, tags):
        if all(tags):
            keys, values = tags
            return [
                {"Name": "tag:%s" % k, "Values": v} for k, v in zip([k[0] for k in keys], values)
            ]
        return None

    def add_single_service_config(self, key, value):
        self.service_config.setdefault(key, value)

    def _compute_config_hash(self, sys_argv):
        filtered_sys_argv = [
            arg for arg in sys_argv if arg not in ["--debug", "--verbose", "--no-cache"]
        ]
        # Be careful to use a hashing mechanism that generates the same hash across
        # different python processes! Otherwise the config file will always be
        # out-of-date
        return hashlib.sha256("".join(sorted(filtered_sys_argv)).encode()).hexdigest()

    def is_up_to_date(self):
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

    def _load_config_hash(self):
        try:
            with self._config_hash_file.open(mode="r", encoding="utf-8") as f:
                return f.read().strip()
        except IOError as e:
            if e.errno != errno.ENOENT:
                # No such file or directory
                raise
            return None

    def _write_config_hash(self):
        store.save_text_to_file(self._config_hash_file, "%s\n" % self._current_config_hash)


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _chunks(list_, length=100):
    return [list_[i : i + length] for i in range(0, len(list_), length)]


def _get_ec2_piggyback_hostname(inst, region):
    # PrivateIpAddress and InstanceId is available although the instance is stopped
    # When we terminate an instance, the instance gets the state "terminated":
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
    # The instance remains in this state about 60 minutes, after 60 minutes the
    # instance is no longer visible in the console.
    # In this case we do not deliever any data for this piggybacked host such that
    # the services go stable and Check_MK service reports "CRIT - Got not information".
    try:
        return "%s-%s-%s" % (inst["PrivateIpAddress"], region, inst["InstanceId"])
    except KeyError:
        return None


def _hostname_from_name_and_region(name, region):
    """
    We add the region to the the hostname because resources in different regions might have the
    same names (for example replicated DynamoDB tables).
    """
    return "%s_%s" % (name, region)


def _elbv2_load_balancer_arn_to_dim(arn):
    # for application load balancers:
    # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/load-balancer-name/load-balancer-id
    # We need: app/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
    # for network load balancers:
    # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/net/load-balancer-name/load-balancer-id
    # We need: net/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
    return "/".join(arn.split("/")[-3:])


def _elbv2_target_group_arn_to_dim(arn):
    return arn.split(":")[-1]


def _describe_dynamodb_tables(client, get_response_content, table_names=None):

    get_table_names = table_names is None
    if get_table_names:
        table_names = []
        for page in client.get_paginator("list_tables").paginate():
            table_names.extend(get_response_content(page, "TableNames"))

    tables = []
    for table_name in table_names:
        try:
            tables.append(
                get_response_content(client.describe_table(TableName=table_name), "Table")
            )
        except client.exceptions.ResourceNotFoundException:
            # we raise the exception if we fetched the table names from the API, since in that case
            # all tables should exist, otherwise something went really wrong
            if get_table_names:
                raise

    return tables


def _validate_wafv2_scope_and_region(scope, region):
    """
    WAFs can either be deployed locally, for example in front of Application Load Balancers,
    or globally, in front of CloudFront. The global ones can only be queried from the region
    us-east-1.
    """

    assert scope in ("REGIONAL", "CLOUDFRONT"), (
        "The scope of WAFV2Limits / WAFV2Summary must be either REGIONAL or CLOUDFRONT, it is "
        "used as the 'Scope' kwarg in the list_... operations of the wafv2 client"
    )

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
) -> List:
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
    client, scope, get_response_content, web_acls_info=None, web_acls_names=None
):
    if web_acls_info is None:
        web_acls_info = _iterate_through_wafv2_list_operations(
            client.list_web_acls, scope, "WebACLs", get_response_content
        )

    if web_acls_names is not None:
        web_acls_info = [
            web_acl_info for web_acl_info in web_acls_info if web_acl_info["Name"] in web_acls_names
        ]

    web_acls = [
        get_response_content(
            client.get_web_acl(Name=web_acl_info["Name"], Scope=scope, Id=web_acl_info["Id"]),
            "WebACL",
        )
        for web_acl_info in web_acls_info
    ]

    return web_acls


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

    def __init__(self):
        self._colleagues = []

    def add(self, colleague):
        self._colleagues.append(colleague)

    def distribute(self, sender, result):
        for colleague in self._colleagues:
            if colleague.name != sender.name:
                colleague.receive(sender, result)


class ResultDistributorS3Limits(ResultDistributor):
    """
    Special mediator for distributing results from S3Limits. This mediator stores any received
    results and distributes both upon receiving and upon adding a new colleague. This is done
    because we want to run S3Limits only once (does not matter for which region, results are the
    same for all regions) and later distribute the results to S3Summary objects in other regions.
    """

    def __init__(self):
        super().__init__()
        self._received_results = {}

    def add(self, colleague):
        super().add(colleague)
        for sender, content in self._received_results.values():
            colleague.receive(sender, content)

    def distribute(self, sender, result):
        self._received_results.setdefault(sender.name, (sender, result))
        super().distribute(sender, result)

    def is_empty(self):
        return len(self._colleagues) == 0


#   ---sections/colleagues--------------------------------------------------


class AWSSectionResults(NamedTuple):
    results: List
    cache_timestamp: float


class AWSSectionResult(NamedTuple):
    piggyback_hostname: AWSStrings
    content: Any


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


AWSCacheFilePath = Path(tmp_dir) / "agents" / "agent_aws"


class AWSSection(DataCache):
    def __init__(self, client, region, config, distributor=None):
        cache_dir = AWSCacheFilePath / region / config.hostname
        super().__init__(cache_dir, self.name)
        self._client = client
        self._region = region
        self._config = config
        self._distributor = ResultDistributor() if distributor is None else distributor
        self._received_results = {}

    @property
    @abc.abstractmethod
    def name(self):
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
    def region(self):
        return self._region

    @property
    def granularity(self) -> int:
        """
        The granularity of the returned data in seconds.
        """
        raise NotImplementedError

    @property
    def period(self):
        return self.validate_period(2 * self.granularity)

    @staticmethod
    def validate_period(period: int, resolution_type: str = "low") -> int:
        """
        What this is all about:
        https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricStat.html
        >>> import pytest
        >>> with pytest.raises(AssertionError):
        ...     [AWSSection.validate_period(p, r) for p, r in [(34, "low"), (45, "high"), (120.0, "low")]]
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

    def _send(self, content):
        self._distributor.distribute(self, content)

    def receive(self, sender, content):
        self._received_results.setdefault(sender.name, content)

    def run(self, use_cache=False):
        colleague_contents = self._get_colleague_contents()
        assert isinstance(colleague_contents, AWSColleagueContents), (
            "%s: Colleague contents must be of type 'AWSColleagueContents'" % self.name
        )
        assert isinstance(colleague_contents.cache_timestamp, float), (
            "%s: Cache timestamp of colleague contents must be of type 'float'" % self.name
        )

        raw_data = self.get_data(colleague_contents, use_cache=use_cache)
        raw_content = AWSRawContent(
            raw_data, self.cache_timestamp if use_cache else NOW.timestamp()
        )
        assert isinstance(raw_content, AWSRawContent), (
            "%s: Raw content must be of type 'AWSRawContent'" % self.name
        )
        assert isinstance(raw_content.cache_timestamp, float), (
            "%s: Cache timestamp of raw content must be of type 'float'" % self.name
        )

        computed_content = self._compute_content(raw_content, colleague_contents)
        assert isinstance(computed_content, AWSComputedContent), (
            "%s: Computed content must be of type 'AWSComputedContent'" % self.name
        )
        assert isinstance(computed_content.cache_timestamp, float), (
            "%s: Cache timestamp of computed content must be of type 'float'" % self.name
        )

        self._send(computed_content)
        created_results = self._create_results(computed_content)
        assert isinstance(created_results, list), (
            "%s: Created results must be fo type 'list'" % self.name
        )

        final_results = []
        for result in created_results:
            assert isinstance(result, AWSSectionResult), (
                "%s: Result must be of type 'AWSSectionResult'" % self.name
            )

            if not result.content:
                logging.info("%s: Result is empty or None", self.name)
                continue

            assert isinstance(result.piggyback_hostname, str), (
                "%s: Piggyback hostname of created result must be of type 'str'" % self.name
            )

            # In the related check plugin aws.include we parse these results and
            # extend list of json-loaded results, except for labels sections.
            self._validate_result_content(result.content)

            final_results.append(result)
        return AWSSectionResults(final_results, computed_content.cache_timestamp)

    def get_validity_from_args(self, *args: Any) -> bool:
        (colleague_contents,) = args
        my_cache_timestamp = self.cache_timestamp
        if my_cache_timestamp is None:
            return False
        if colleague_contents.cache_timestamp > my_cache_timestamp:
            logging.info("Colleague data is newer than cache file %s", self._cache_file)
            return False
        return True

    @abc.abstractmethod
    def _get_colleague_contents(self: Any) -> AWSColleagueContents:
        """
        Receive section contents from colleagues. The results are stored in
        self._receive_results: {<KEY>: AWSComputedContent}.
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
        self, raw_content: AWSRawContent, colleague_contents: Any
    ) -> AWSComputedContent:
        """
        Compute the final content of this section based on the raw content of
        this section and the content received from the optional colleague
        sections.
        """

    @abc.abstractmethod
    def _create_results(self, computed_content: Any) -> List[AWSSectionResult]:
        pass

    def _get_response_content(self, response, key, dflt=None):
        if dflt is None:
            dflt = []
        try:
            return response[key]
        except KeyError:
            logging.info("%s: KeyError; Available keys are %s", self.name, response)
            return dflt

    def _validate_result_content(self, content):
        assert isinstance(content, list), "%s: Result content must be of type 'list'" % self.name

    def _prepare_tags_for_api_response(self, tags):
        """
        We need to change the format, in order to filter out instances with specific
        tags if and only if we already fetched instances, eg. by limits section.
        The format:
        [{'Key': KEY, 'Value': VALUE}, ...]
        """
        if not tags:
            return None
        prepared_tags = []
        for tag in tags:
            tag_name = tag["Name"]
            if tag_name.startswith("tag:"):
                tag_key = tag_name[4:]
            else:
                tag_key = tag_name
            prepared_tags.extend([{"Key": tag_key, "Value": v} for v in tag["Values"]])
        return prepared_tags


class AWSSectionLimits(AWSSection):
    def __init__(self, client, region, config, distributor=None, quota_client=None):
        super().__init__(client, region, config, distributor=distributor)
        self._quota_client = quota_client
        self._limits = {}

    def _add_limit(self, piggyback_hostname, limit, region=None):
        assert isinstance(limit, AWSLimit), "%s: Limit must be of type 'AWSLimit'" % self.name
        if region is None:
            region = self._region
        else:
            assert isinstance(region, str), "%s: Region for limit must be of type str" % self.name

        self._limits.setdefault(piggyback_hostname, []).append(
            AWSRegionLimit(
                key=limit.key,
                title=limit.title,
                limit=limit.limit,
                amount=limit.amount,
                region=region,
            )
        )

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, limits)
            for piggyback_hostname, limits in self._limits.items()
        ]


class AWSSectionLabels(AWSSection):
    def _create_results(self, computed_content):
        assert isinstance(computed_content.content, dict), (
            "%s: Computed result of Labels section must be of type 'dict'" % self.name
        )
        for pb in computed_content.content:
            assert bool(pb), "%s: Piggyback hostname is not allowed to be empty" % self.name
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]

    def _validate_result_content(self, content):
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


class AWSSectionCloudwatch(AWSSection):
    def get_live_data(self, *args):
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
            response = self._client.get_metric_data(
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
    def _get_metrics(self, colleague_contents):
        pass

    def _create_id_for_metric_data_query(self, index, metric_name, *args):
        """
        ID field must be unique in a single call.
        The valid characters are letters, numbers, and underscore.
        The first character must be a lowercase letter.
        Regex: ^[a-z][a-zA-Z0-9_]*$
        """
        return "_".join(["id", str(index)] + list(args) + [metric_name])

    def _extend_metrics_by_period(self, metrics, raw_content):
        """
        Extend the queried metric values by the corresponding time period. For metrics based on the
        "Sum" statistics, we add the actual time period which can then be used by the check plugins
        to compute a rate. For all other metrics, we add 'None', such that the metric values are
        always 2-tuples (value, period), where period is either an actual time period such as 600 s
        or None.
        """
        for metric_specs, metric_contents in zip(metrics, raw_content):
            metric_stat = metric_specs["MetricStat"]
            if metric_stat["Stat"] == "Sum":
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
# The GetCostAndUsageRequest operation supports only DAILY and MONTHLY granularities.


class CostsAndUsage(AWSSection):
    @property
    def name(self):
        return "costs_and_usage"

    @property
    def cache_interval(self):
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        granularity_name, granularity_interval = "DAILY", self.granularity
        fmt = "%Y-%m-%d"
        response = self._client.get_cost_and_usage(
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

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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
    def name(self):
        return "ec2_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        quotas = self._get_response_content(
            self._quota_client.list_service_quotas(ServiceCode="ec2"), "Quotas"
        )

        response = self._client.describe_instances()
        reservations = self._get_response_content(response, "Reservations")

        response = self._client.describe_reserved_instances()
        reserved_instances = self._get_response_content(response, "ReservedInstances")

        response = self._client.describe_addresses()
        addresses = self._get_response_content(response, "Addresses")

        response = self._client.describe_security_groups()
        security_groups = self._get_response_content(response, "SecurityGroups")

        response = self._client.describe_network_interfaces()
        interfaces = self._get_response_content(response, "NetworkInterfaces")

        response = self._client.describe_spot_instance_requests()
        spot_inst_requests = self._get_response_content(response, "SpotInstanceRequests")

        response = self._client.describe_spot_fleet_requests()
        spot_fleet_requests = self._get_response_content(response, "SpotFleetRequestConfigs")

        return (
            reservations,
            reserved_instances,
            addresses,
            security_groups,
            interfaces,
            spot_inst_requests,
            spot_fleet_requests,
            quotas,
        )

    def _compute_content(self, raw_content, colleague_contents):
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

    def _add_instance_limits(self, instances, res_instances, spot_inst_requests, instance_quotas):
        inst_limits = self._get_inst_limits(instances, spot_inst_requests)
        res_limits = self._get_res_inst_limits(res_instances)

        total_ris = 0
        running_ris = 0
        ondemand_limits: Dict[str, int] = {}
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
                inst_fam_name = AWSEC2InstFamilies.get(inst_type[0], "Unknown Instance Family")
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
        inst_limits: Dict[str, Dict[str, int]] = {}
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
        res_limits: Dict[str, Dict[str, int]] = {}
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

    def _add_addresses_limits(self, addresses):
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
                "VPC Elastic IP Addresses",
                5,
                vpc_addresses,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "elastic_ip_addresses",
                "Elastic IP Addresses",
                5,
                std_addresses,
            ),
        )

    def _add_security_group_limits(self, security_groups):

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

    def _add_interface_limits(self, interfaces):
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

    def _add_spot_inst_limits(self, spot_inst_requests):
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

    def _add_spot_fleet_limits(self, spot_fleet_requests):
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
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ec2_names"]
        self._tags = self._config.service_config["ec2_tags"]

    @property
    def name(self):
        return "ec2_summary"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("ec2_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        if self._tags is None and self._names is not None:
            return self._fetch_instances_filtered_by_names(colleague_contents.content)
        if self._tags is not None:
            return self._fetch_instances_filtered_by_tags(colleague_contents.content)
        return self._fetch_instances_without_filter()

    def _fetch_instances_filtered_by_names(self, col_reservations):
        if col_reservations:
            instances = [
                inst
                for res in col_reservations
                for inst in res["Instances"]
                if inst["InstanceId"] in self._names
            ]
        else:
            response = self._client.describe_instances(InstanceIds=self._names)
            instances = [
                inst
                for res in self._get_response_content(response, "Reservations")
                for inst in res["Instances"]
            ]
        return instances

    def _fetch_instances_filtered_by_tags(self, col_reservations):
        if col_reservations:
            tags = self._prepare_tags_for_api_response(self._tags)
            return [
                inst
                for res in col_reservations
                for inst in res["Instances"]
                for tag in inst["Tags"]
                if tag in tags
            ]

        instances = []
        for chunk in _chunks(self._tags, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_instances(Filters=chunk)
            instances.extend(
                [
                    inst
                    for res in self._get_response_content(response, "Reservations")
                    for inst in res["Instances"]
                ]
            )
        return instances

    def _fetch_instances_without_filter(self):
        response = self._client.describe_instances()
        return [
            inst
            for res in self._get_response_content(response, "Reservations")
            for inst in res["Instances"]
        ]

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            self._format_instances(raw_content.content), raw_content.cache_timestamp
        )

    def _format_instances(self, instances):
        formatted_instances = {}
        for inst in instances:
            inst_id = _get_ec2_piggyback_hostname(inst, self._region)
            if inst_id:
                formatted_instances[inst_id] = inst
        return formatted_instances

    def _create_results(self, computed_content):
        return [AWSSectionResult("", list(computed_content.content.values()))]


class EC2Labels(AWSSectionLabels):
    @property
    def name(self):
        return "ec2_labels"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        tags_to_filter = [
            {
                "Name": "resource-id",
                "Values": [inst["InstanceId"] for inst in colleague_contents.content.values()],
            }
        ]
        tags = []
        for chunk in _chunks(tags_to_filter, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_tags(Filters=chunk)
            tags.extend(self._get_response_content(response, "Tags"))
        return tags

    def _compute_content(self, raw_content, colleague_contents):
        inst_id_to_ec2_piggyback_hostname_map = {
            inst["InstanceId"]: ec2_instance_id
            for ec2_instance_id, inst in colleague_contents.content.items()
        }

        computed_content: Dict[str, Dict[str, str]] = {}
        for tag in raw_content.content:
            ec2_piggyback_hostname = inst_id_to_ec2_piggyback_hostname_map.get(tag["ResourceId"])
            if not ec2_piggyback_hostname:
                continue
            computed_content.setdefault(ec2_piggyback_hostname, {}).setdefault(
                tag["Key"], tag["Value"]
            )

        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class EC2SecurityGroups(AWSSection):
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ec2_names"]
        self._tags = self._config.service_config["ec2_tags"]

    @property
    def name(self):
        return "ec2_security_groups"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        sec_groups = self._describe_security_groups()
        return {group["GroupId"]: group for group in sec_groups}

    def _describe_security_groups(self):
        if self._names is not None:
            response = self._client.describe_security_groups(InstanceIds=self._names)
            return self._get_response_content(response, "SecurityGroups")

        if self._tags is not None:
            sec_groups = []
            for chunk in _chunks(self._tags, length=200):
                # EC2 FilterLimitExceeded: The maximum number of filter values
                # specified on a single call is 200
                response = self._client.describe_security_groups(Filters=chunk)
                sec_groups.extend(self._get_response_content(response, "SecurityGroups"))
            return sec_groups

        response = self._client.describe_security_groups()
        return self._get_response_content(response, "SecurityGroups")

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for instance_name, instance in colleague_contents.content.items():
            for security_group_from_instance in instance.get("SecurityGroups", []):
                security_group = raw_content.content.get(security_group_from_instance["GroupId"])
                if security_group is None:
                    continue
                content_by_piggyback_hosts.setdefault(instance_name, []).append(security_group)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class EC2(AWSSectionCloudwatch):
    @property
    def name(self):
        return "ec2"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("ec2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
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

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
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
    def name(self):
        return "ebs_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        response = self._client.describe_volumes()
        volumes = self._get_response_content(response, "Volumes")

        response = self._client.describe_snapshots(OwnerIds=["self"])
        snapshots = self._get_response_content(response, "Snapshots")
        return volumes, snapshots

    def _compute_content(self, raw_content, colleague_contents):
        volumes, snapshots = raw_content.content

        vol_storage_standard = 0
        vol_storage_io1 = 0
        vol_storage_gp2 = 0
        vol_storage_sc1 = 0
        vol_storage_st1 = 0
        vol_iops_io1 = 0
        for volume in volumes:
            vol_type = volume["VolumeType"]
            vol_size = volume["Size"]
            if vol_type == "standard":
                vol_storage_standard += vol_size
            elif vol_type == "io1":
                vol_storage_io1 += vol_size
                vol_iops_io1 += volume["Iops"]
            elif vol_type == "gp2":
                vol_storage_gp2 += vol_size
            elif vol_type == "sc1":
                vol_storage_sc1 += vol_size
            elif vol_type == "st1":
                vol_storage_st1 += vol_size
            else:
                logging.info("%s: Unhandled volume type: '%s'", self.name, vol_type)

        # These are total limits and not instance specific
        # Space values are in TiB.
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
                "Provisioned IOPS SSD space",
                300,
                vol_storage_io1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_iops_io1",
                "Provisioned IOPS SSD IO operations per second",
                300000,
                vol_storage_io1,
            ),
        )
        self._add_limit(
            "",
            AWSLimit(
                "block_store_space_gp2",
                "General Purpose SSD space",
                300,
                vol_storage_gp2,
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
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["ebs_names"]
        self._tags = self._config.service_config["ebs_tags"]

    @property
    def name(self):
        return "ebs_summary"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
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

    def get_live_data(self, *args):
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
            response = self._client.describe_volume_status(VolumeIds=[vol_id])
            for state in self._get_response_content(response, "VolumeStatuses"):
                if state["VolumeId"] == vol_id:
                    vol.setdefault("VolumeStatus", state["VolumeStatus"])
        return formatted_volumes

    def _fetch_volumes_filtered_by_names(self, col_volumes):
        if col_volumes:
            return [v for v in col_volumes if v["VolumeId"] in self._names]
        response = self._client.describe_volumes(VolumeIds=self._names)
        return self._get_response_content(response, "Volumes")

    def _fetch_volumes_filtered_by_tags(self, col_volumes):
        if col_volumes:
            tags = self._prepare_tags_for_api_response(self._tags)
            return [v for v in col_volumes for tag in v.get("Tags", []) if tag in tags]

        volumes = []
        for chunk in _chunks(self._tags, length=200):
            # EC2 FilterLimitExceeded: The maximum number of filter values
            # specified on a single call is 200
            response = self._client.describe_volumes(Filters=chunk)
            volumes.extend(self._get_response_content(response, "Volumes"))
        return volumes

    def _fetch_volumes_without_filter(self, col_volumes):
        if col_volumes:
            return col_volumes
        response = self._client.describe_volumes()
        return self._get_response_content(response, "Volumes")

    def _compute_content(self, raw_content, colleague_contents):
        _col_volumes, col_instances = colleague_contents.content
        instance_name_mapping = {v["InstanceId"]: k for k, v in col_instances.items()}

        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for vol in raw_content.content.values():
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

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class EBS(AWSSectionCloudwatch):
    @property
    def name(self):
        return "ebs"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
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

    def _get_metrics(self, colleague_contents):
        muv: List[Tuple[str, str, List[str]]] = [
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
        metrics = []
        for idx, (instance_name, volume_name, volume_type) in enumerate(colleague_contents.content):
            for metric_name, unit, volume_types in muv:
                if volume_types and volume_type not in volume_types:
                    continue
                metric = {
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

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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
    def list_buckets(client):
        """
        Get all buckets with LocationConstraint
        """
        bucket_list = client.list_buckets()
        for bucket in bucket_list["Buckets"]:
            bucket_name = bucket["Name"]

            # request additional LocationConstraint information
            try:
                response = client.get_bucket_location(Bucket=bucket_name)
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
    def name(self):
        return "s3_limits"

    @property
    def cache_interval(self):
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)

        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        There's no API method for getting account limits thus we have to
        fetch all buckets.
        """
        bucket_list = S3BucketHelper.list_buckets(self._client)
        return bucket_list

    def _compute_content(self, raw_content, colleague_contents):
        self._add_limit(
            "", AWSLimit("buckets", "Buckets", 100, len(raw_content.content)), region="Global"
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class S3Summary(AWSSection):
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["s3_names"]
        self._tags = self._prepare_tags_for_api_response(self._config.service_config["s3_tags"])

    @property
    def name(self):
        return "s3_summary"

    @property
    def cache_interval(self):
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get("s3_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        found_buckets = []
        for bucket in self._list_buckets(colleague_contents):
            bucket_name = bucket["Name"]

            try:
                response = self._client.get_bucket_tagging(Bucket=bucket_name)
            except self._client.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.info("%s/%s: No tags set, %s", self.name, bucket_name, e)
                response = {}

            tagging = self._get_response_content(response, "TagSet")
            if self._matches_tag_conditions(tagging):
                bucket["Tagging"] = tagging
                found_buckets.append(bucket)
        return found_buckets

    def _list_buckets(self, colleague_contents):
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

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            {bucket["Name"]: bucket for bucket in raw_content.content}, raw_content.cache_timestamp
        )

    def _create_results(self, computed_content):
        return [AWSSectionResult("", None)]


class S3(AWSSectionCloudwatch):
    @property
    def name(self):
        return "s3"

    @property
    def cache_interval(self):
        # BucketSizeBytes and NumberOfObjects are available per day
        # and must include 00:00h
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get("s3_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
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

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row["Label"])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


class S3Requests(AWSSectionCloudwatch):
    @property
    def name(self):
        return "s3_requests"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("s3_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
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

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row["Label"])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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
    def name(self):
        return "glacier_limits"

    @property
    def cache_interval(self):
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        There's no API method for getting account limits thus we have to
        fetch all vaults.
        """
        response = self._client.list_vaults()
        return self._get_response_content(response, "VaultList")

    def _compute_content(self, raw_content, colleague_contents):
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


class GlacierSummary(AWSSection):
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["glacier_names"]
        self._tags = self._prepare_tags_for_api_response(
            self._config.service_config["glacier_tags"]
        )

    @property
    def name(self):
        return "glacier_summary"

    @property
    def cache_interval(self):
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get("glacier_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
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
                response = self._client.list_tags_for_vault(vaultName=vault_name)
            except botocore.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.warning("%s/%s: Exception, %s", self.name, vault_name, e)
                response = {}

            tagging = self._get_response_content(response, "Tags")
            if self._matches_tag_conditions(tagging):
                vault["Tagging"] = tagging
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

    def _list_vaults(self, colleague_contents):
        """
        get list of vaults from previous call or get it now
        :param colleague_contents:
        :return:
        """
        if colleague_contents and colleague_contents.content:
            return colleague_contents.content
        return self._get_response_content(self._client.list_vaults(), "VaultList")

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", None)]


class Glacier(AWSSection):
    @property
    def name(self):
        return "glacier"

    @property
    def cache_interval(self):
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = get_seconds_since_midnight(NOW)
        logging.debug("Maximal allowed age of usage data cache: %s sec", cache_interval)
        return cache_interval

    @property
    def granularity(self):
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get("glacier_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        pass

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(colleague_contents.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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
    def name(self):
        return "elb_limits"

    @property
    def cache_interval(self):
        # If you change this, you might have to adjust factory_settings['levels_spillover'] in
        # checks/aws_elb
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
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

        response = self._client.describe_account_limits()
        limits = self._get_response_content(response, "Limits")
        return load_balancers, limits

    def _compute_content(self, raw_content, colleague_contents):
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
    def __init__(self, client, region, config, distributor=None, resource=""):

        self._resource = resource
        if self._resource == "elb":
            self._describe_load_balancers_karg = "LoadBalancerNames"
            self._describe_load_balancers_key = "LoadBalancerDescriptions"
        elif self._resource == "elbv2":
            self._describe_load_balancers_karg = "Names"
            self._describe_load_balancers_key = "LoadBalancers"
        else:
            raise AssertionError(
                "ELBSummaryGeneric: resource argument must be either 'elb' or " "'elbv2'"
            )

        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["%s_names" % resource]
        self._tags = self._prepare_tags_for_api_response(
            self._config.service_config["%s_tags" % resource]
        )

    @property
    def name(self):
        return "%s_summary" % self._resource

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("%s_limits" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
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
                load_balancer["TagDescriptions"] = tagging
                found_load_balancers.append(load_balancer)
        return found_load_balancers

    def _get_load_balancer_tags(self, load_balancer):
        if self._resource == "elb":
            return self._client.describe_tags(LoadBalancerNames=[load_balancer["LoadBalancerName"]])
        return self._client.describe_tags(ResourceArns=[load_balancer["LoadBalancerArn"]])

    def _describe_load_balancers(self, colleague_contents):
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

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, str] = {}
        for load_balancer in raw_content.content:
            content_by_piggyback_hosts.setdefault(load_balancer["DNSName"], load_balancer)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", list(computed_content.content.values()))]


class ELBLabelsGeneric(AWSSectionLabels):
    def __init__(self, client, region, config, distributor=None, resource=""):
        self._resource = resource
        super().__init__(client, region, config, distributor=distributor)

    @property
    def name(self):
        return "%s_generic_labels" % self._resource

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("%s_summary" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        return colleague_contents.content

    def _compute_content(self, raw_content, colleague_contents):
        computed_content = {
            elb_instance_id: {tag["Key"]: tag["Value"] for tag in data.get("TagDescriptions", [])}
            for elb_instance_id, data in raw_content.content.items()
        }
        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class ELBHealth(AWSSection):
    @property
    def name(self):
        return "elb_health"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("elb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        load_balancers: Dict[str, List[str]] = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.items():
            load_balancer_name = load_balancer["LoadBalancerName"]
            response = self._client.describe_instance_health(LoadBalancerName=load_balancer_name)
            states = self._get_response_content(response, "InstanceStates")
            if states:
                load_balancers.setdefault(load_balancer_dns_name, states)
        return load_balancers

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.items()
        ]


class ELB(AWSSectionCloudwatch):
    @property
    def name(self):
        return "elb"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("elb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
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

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
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
    def name(self):
        return "elbv2_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
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

            response = self._client.describe_target_groups(LoadBalancerArn=lb_arn)
            load_balancer["TargetGroups"] = self._get_response_content(response, "TargetGroups")

            response = self._client.describe_listeners(LoadBalancerArn=lb_arn)
            listeners = self._get_response_content(response, "Listeners")
            load_balancer["Listeners"] = listeners

            if load_balancer["Type"] == "application":
                rules = []
                for listener in listeners:
                    response = self._client.describe_rules(ListenerArn=listener["ListenerArn"])
                    rules.extend(self._get_response_content(response, "Rules"))

                # Limit 100 holds for rules which are not default, see AWS docs:
                # https://docs.aws.amazon.com/de_de/general/latest/gr/aws_service_limits.html
                # > Limits für Elastic Load Balancing
                load_balancer["Rules"] = [rule for rule in rules if not rule["IsDefault"]]

        response = self._client.describe_account_limits()
        limits = self._get_response_content(response, "Limits")
        return load_balancers, limits

    def _compute_content(self, raw_content, colleague_contents):
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
                "Load balancers Target Groups",
                limits["target-groups"],
                target_groups_count,
            ),
        )
        return AWSComputedContent(load_balancers, raw_content.cache_timestamp)


class ELBv2TargetGroups(AWSSection):
    @property
    def name(self):
        return "elbv2_target_groups"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        load_balancers: Dict[str, List[Tuple[str, List[str]]]] = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.items():
            load_balancer_type = load_balancer.get("Type")
            if load_balancer_type not in ["application", "network"]:
                # Just to be sure, that we do not describe target groups of other lbs
                continue

            if "TargetGroups" not in load_balancer:
                response = self._client.describe_target_groups(
                    LoadBalancerArn=load_balancer["LoadBalancerArn"]
                )
                load_balancer["TargetGroups"] = self._get_response_content(response, "TargetGroups")

            target_groups = load_balancer.get("TargetGroups", [])
            for target_group in target_groups:
                response = self._client.describe_target_health(
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

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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
    def name(self):
        return "elbv2_application"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
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

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class ELBv2ApplicationTargetGroupsResponses(AWSSectionCloudwatch):
    """
    Additional monitoring for target groups of application load balancers.
    """

    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._separator = " "

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics_with_specs(self, colleague_contents, target_types, metrics_to_get):

        metrics = []

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

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[Any]] = {}
        for row in raw_content.content:
            load_bal_dns, target_group_name = row["Label"].split(self._separator)
            row["Label"] = target_group_name
            content_by_piggyback_hosts.setdefault(load_bal_dns, []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class ELBv2ApplicationTargetGroupsHTTP(ELBv2ApplicationTargetGroupsResponses):
    @property
    def name(self):
        return "elbv2_application_target_groups_http"

    def _get_metrics(self, colleague_contents):
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
    def name(self):
        return "elbv2_application_target_groups_lambda"

    def _get_metrics(self, colleague_contents):
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
    def name(self):
        return "elbv2_network"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
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

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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

AWSRDSLimitNameMap = {
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
    def name(self):
        return "rds_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        AWS/RDS API method 'describe_account_attributes' already sends
        limit and usage values.
        """
        response = self._client.describe_account_attributes()
        return self._get_response_content(response, "AccountQuotas")

    def _compute_content(self, raw_content, colleague_contents):
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
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["rds_names"]
        self._tags = self._prepare_tags_for_api_response(self._config.service_config["rds_tags"])

    @property
    def name(self):
        return "rds_summary"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):

        db_instances = []

        for instance in self._describe_db_instances():
            tags = self._get_instance_tags(instance)
            if self._matches_tag_conditions(tags):
                instance["Region"] = self._region
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
            except self._client.exceptions.DBInstanceNotFoundFault:
                pass

        return instances

    def _get_instance_tags(self, instance):
        # list_tags_for_resource cannot be paginated
        return self._get_response_content(
            self._client.list_tags_for_resource(ResourceName=instance["DBInstanceArn"]), "TagList"
        )

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            {instance["DBInstanceIdentifier"]: instance for instance in raw_content.content},
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content):
        return [AWSSectionResult("", list(computed_content.content.values()))]


class RDS(AWSSectionCloudwatch):
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._separator = " "

    @property
    def name(self):
        return "rds"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("rds_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        # the documentation
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MonitoringOverview.html
        # seems to be partially wrong: FailedSQLServerAgentJobsCount has to be queried in Counts
        # (instead of Count/Minute) and OldestReplicationSlotLag, ReplicationSlotDiskUsage and
        # TransactionLogsDiskUsage have to be queried in Bytes (instead of Megabytes)
        metrics = []
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
                metric = {
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

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            instance_id = row["Label"].split(self._separator)[0]
            row.update(colleague_contents.content.get(instance_id, {}))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


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
    def name(self):
        return "cloudwatch_alarms_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        response = self._client.describe_alarms()
        return self._get_response_content(response, "MetricAlarms")

    def _compute_content(self, raw_content, colleague_contents):
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
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["cloudwatch_alarms"]

    @property
    def name(self):
        return "cloudwatch_alarms"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("cloudwatch_alarms_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args
        if self._names:
            if colleague_contents.content:
                return [
                    alarm
                    for alarm in colleague_contents.content
                    if alarm["AlarmName"] in self._names
                ]
            response = self._client.describe_alarms(AlarmNames=self._names)
        else:
            response = self._client.describe_alarms()
        return self._get_response_content(response, "MetricAlarms")

    def _compute_content(self, raw_content, colleague_contents):
        if raw_content.content:
            return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)
        dflt_alarms = [{"AlarmName": "Check_MK/CloudWatch Alarms", "StateValue": "NO_ALARMS"}]
        return AWSComputedContent(dflt_alarms, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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


class DynamoDBLimits(AWSSectionLimits):
    @property
    def name(self):
        return "dynamodb_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        """
        The AWS/DynamoDB API method 'describe_limits' provides limits only, but no usage data. We
        therefore gather a list of tables using the method 'list_tables' and check the usage of each
        table via 'describe_table'. See also
        https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_DescribeLimits.html.
        """
        limits = self._client.describe_limits()
        tables = _describe_dynamodb_tables(self._client, self._get_response_content)
        return tables, limits

    def _add_read_write_limits(
        self, piggyback_hostname, read_usage, write_usage, read_limit, write_limit
    ):

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

    def _compute_content(self, raw_content, colleague_contents):

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
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["dynamodb_names"]
        self._tags = self._prepare_tags_for_api_response(
            self._config.service_config["dynamodb_tags"]
        )

    @property
    def name(self):
        return "dynamodb_summary"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("dynamodb_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
        (colleague_contents,) = args

        found_tables = []

        for table in self._describe_tables(colleague_contents):
            tags = self._get_table_tags(table)

            if self._matches_tag_conditions(tags):
                table["Region"] = self._region
                found_tables.append(table)

        return found_tables

    def _get_table_tags(self, table):
        tags = []
        paginator = self._client.get_paginator("list_tags_of_resource")
        response_iterator = paginator.paginate(ResourceArn=table["TableArn"])
        for page in response_iterator:
            tags.extend(self._get_response_content(page, "Tags"))
        return tags

    def _describe_tables(self, colleague_contents):

        if self._names is None:
            if colleague_contents.content:
                return colleague_contents.content
            return _describe_dynamodb_tables(self._client, self._get_response_content)

        if colleague_contents.content:
            return [
                table for table in colleague_contents.content if table["TableName"] in self._names
            ]
        return _describe_dynamodb_tables(
            self._client, self._get_response_content, table_names=self._names
        )

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, str] = {}
        for table in raw_content.content:
            content_by_piggyback_hosts.setdefault(
                _hostname_from_name_and_region(table["TableName"], self._region), table
            )
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", list(computed_content.content.values()))]


class DynamoDBTable(AWSSectionCloudwatch):
    @property
    def name(self):
        return "dynamodb_table"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("dynamodb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):

        metrics = []

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

                dimensions = [{"Name": "TableName", "Value": table["TableName"]}]

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

    def _compute_content(self, raw_content, colleague_contents):

        content_by_piggyback_hosts: Dict[str, List[Dict]] = {}
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

    def _create_results(self, computed_content):
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
    def __init__(self, client, region, config, scope, distributor=None, quota_client=None):
        super().__init__(client, region, config, distributor=distributor, quota_client=quota_client)
        self._region_report = _validate_wafv2_scope_and_region(scope, self._region)
        self._scope = scope

    @property
    def name(self):
        return "wafv2_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
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

        resources: Dict = {}

        for list_operation, key in [
            (self._client.list_web_acls, "WebACLs"),
            (self._client.list_rule_groups, "RuleGroups"),
            (self._client.list_ip_sets, "IPSets"),
            (self._client.list_regex_pattern_sets, "RegexPatternSets"),
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

    def _compute_content(self, raw_content, colleague_contents):
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
    def __init__(self, client, region, config, scope, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._region_report = _validate_wafv2_scope_and_region(scope, self._region)
        self._scope = scope
        self._names = self._config.service_config["wafv2_names"]
        self._tags = self._prepare_tags_for_api_response(self._config.service_config["wafv2_tags"])

    @property
    def name(self):
        return "wafv2_summary"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("wafv2_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):

        (colleague_contents,) = args
        found_web_acls = []

        for web_acl in self._describe_web_acls(colleague_contents):
            # list_tags_for_resource does not support pagination
            tag_info = self._get_response_content(
                self._client.list_tags_for_resource(ResourceARN=web_acl["ARN"]),
                "TagInfoForResource",
                dflt={},
            )
            tags = self._get_response_content(tag_info, "TagList")

            if self._matches_tag_conditions(tags):
                web_acl["Region"] = self._region_report
                found_web_acls.append(web_acl)

        return found_web_acls

    def _describe_web_acls(self, colleague_contents):

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

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, str] = {}
        for web_acl in raw_content.content:
            content_by_piggyback_hosts.setdefault(
                _hostname_from_name_and_region(web_acl["Name"], self._region_report), web_acl
            )
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", list(computed_content.content.values()))]


class WAFV2WebACL(AWSSectionCloudwatch):
    def __init__(self, client, region, config, is_regional, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        if not is_regional:
            assert self._region == "us-east-1", (
                "WAFV2WebACL: is_regional should only be set to "
                "False in combination with the region us-east-1, "
                "since metrics for CloudFront-WAFs can only be "
                "accessed from this region"
            )
        self._metric_dimensions: List[Dict] = [
            {"Name": "WebACL", "Value": None},
            {"Name": "Rule", "Value": "ALL"},
        ]
        if is_regional:
            self._metric_dimensions.append({"Name": "Region", "Value": self._region})

    @property
    def name(self):
        return "wafv2_web_acl"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get("wafv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):

        metrics = []

        for idx, (piggyback_hostname, web_acl) in enumerate(colleague_contents.content.items()):

            self._metric_dimensions[0]["Value"] = web_acl["Name"]

            for metric_name in ["AllowedRequests", "BlockedRequests"]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": piggyback_hostname,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/WAFV2",
                                "MetricName": metric_name,
                                "Dimensions": self._metric_dimensions,
                            },
                            "Period": self.period,
                            "Stat": "Sum",
                        },
                    }
                )

        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts: Dict[str, List[Dict]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
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
    def name(self):
        return "lambda_region_limits"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, *args):
        return self._client.get_account_settings()

    def _compute_content(self, raw_content, colleague_contents):
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
    def __init__(self, client, region, config, distributor=None):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["lambda_names"]
        self._tags = self._prepare_tags_for_api_response(self._config.service_config["lambda_tags"])

    @property
    def name(self):
        return "lambda_summary"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, *args):
        functions = []
        for page in self._client.get_paginator("list_functions").paginate():
            for function in self._get_response_content(page, "Functions"):
                if (
                    self._names is None
                    or (self._names and function.get("FunctionName") in self._names)
                ) and (
                    self._tags is None
                    or self._tags
                    and self._matches_tag_conditions(self._get_tagging_for(function))
                ):
                    functions.append(function)
        return functions

    def _get_tagging_for(self, function):
        tagging = self._get_response_content(
            self._client.list_tags(Resource=function.get("FunctionArn")), "Tags"
        )
        # adapt to format of _prepare_tags_for_api_response
        return [{"Key": key, "Value": value} for key, value in tagging.items()]

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


def _function_arn_to_function_name_dim(function_arn: str) -> str:
    """
    >>> _function_arn_to_function_name_dim("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function")
    'my_python_test_function'
    """
    return function_arn.split(":")[6]


class LambdaCloudwatch(AWSSectionCloudwatch):
    @property
    def name(self):
        return "lambda"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
        # lambda_provisioned_concurrency has to be used, because some metrics for provisioned concurrency will only
        # be reported if the ARN for the provisioned concurrency configuration is used.
        # lambda_provisioned_concurrency contains also the ARNs for lambda functions without provisioned conurrency.
        colleague = self._received_results.get("lambda_provisioned_concurrency")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        def _get_function_arns(colleague_content):
            function_arns = []
            for function_arn, provisioned_concurrency_configurations in colleague_content.items():
                for config in provisioned_concurrency_configurations:
                    function_arns.append(config["FunctionArn"])
                function_arns.append(function_arn)
            return function_arns

        def _create_dimensions(function_arn):
            def _function_arn_to_resource_dim(function_arn: str) -> Optional[str]:
                """
                >>> _function_arn_to_resource_dim("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function:AliasOrVersionNumber")
                'my_python_test_function:AliasOrVersionNumber'
                """
                splitted = function_arn.split(":")
                return f"{splitted[6]}:{splitted[7]}" if len(splitted) == 8 else None

            dimensions = [
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

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


class LambdaProvisionedConcurrency(AWSSection):
    @property
    def name(self):
        return "lambda_provisioned_concurrency"

    @property
    def cache_interval(self):
        return 300

    @property
    def granularity(self):
        return 300

    def _get_colleague_contents(self):
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

    def get_live_data(self, *args: AWSComputedContent) -> ProvisionedConcurrencyConfigs:
        (colleague_contents,) = args
        return {
            lambda_function["FunctionArn"]: self._list_provisioned_concurrency_configs(
                lambda_function["FunctionName"]
            )
            for lambda_function in colleague_contents.content
        }

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ):
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent):
        return [AWSSectionResult("", computed_content.content)]

    def _validate_result_content(self, content):
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


LambdaMetricStats = Sequence[Mapping[str, str]]


class LambdaCloudwatchInsights(AWSSection):
    def __init__(
        self,
        client,
        region: str,
        config: AWSConfig,
        distributor: Optional[ResultDistributor] = None,
    ):
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["lambda_names"]
        self._tags = self._prepare_tags_for_api_response(self._config.service_config["lambda_tags"])

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
        *, client, query_id: str, timeout_seconds: float, sleep_duration=0.1
    ) -> Optional[LambdaMetricStats]:
        "Synchronous wrapper for asynchronous query API with timeout checking. (agent should not be blocked)."
        response_results: Mapping[str, Any] = {"status": "Scheduled"}
        query_start = datetime.now().timestamp()
        while response_results["status"] != "Complete":
            response_results = client.get_query_results(queryId=query_id)
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
            response_results["results"][0]
            if response_results["results"] and response_results["status"] == "Complete"
            else None
        )

    def _query_with_cloudwatch_insights(
        self, *, log_group_name: str, query_string: str, timeout_seconds: int
    ) -> Optional[LambdaMetricStats]:
        end_time_seconds = int(NOW.timestamp())
        start_time_seconds = int(end_time_seconds - self.period)
        response_query_id = self._client.start_query(
            logGroupName=log_group_name,
            startTime=start_time_seconds,
            endTime=end_time_seconds,
            queryString=query_string,
        )
        return self.query_results(
            client=self._client,
            query_id=response_query_id["queryId"],
            timeout_seconds=timeout_seconds,
        )

    def get_live_data(
        self, *args: AWSColleagueContents
    ) -> Mapping[str, Optional[LambdaMetricStats]]:
        (colleague_contents,) = args
        return {
            function_arn: results
            for function_arn in colleague_contents.content.keys()
            if (
                results := self._query_with_cloudwatch_insights(
                    log_group_name=f"/aws/lambda/{_function_arn_to_function_name_dim(function_arn)}",
                    query_string='filter @type = "REPORT"'
                    "| stats "
                    "max(@maxMemoryUsed) as max_memory_used_bytes,"
                    "max(@initDuration) as max_init_duration_ms,"
                    'sum(strcontains(@message, "Init Duration")) as count_cold_starts,'
                    "count() as count_invocations",
                    timeout_seconds=30,
                )
            )
        }

    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content: AWSComputedContent) -> List[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]

    def _validate_result_content(self, content: AWSSectionResult) -> None:
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
    Type: str
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
    def __init__(self, client, region, config, distributor=None) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["route53_names"]
        self._tags = self._prepare_tags_for_api_response(
            self._config.service_config["route53_tags"]
        )

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

    def get_live_data(self, *args) -> Sequence[HealthCheck]:
        return list(
            itertools.chain.from_iterable(
                self._get_response_content(page, "HealthChecks")
                for page in self._client.get_paginator("list_health_checks").paginate()
            )
        )

    def _compute_content(self, raw_content, colleague_contents) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    def _create_results(self, computed_content) -> List[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class Route53Cloudwatch(AWSSectionCloudwatch):
    def __init__(self, client, region, config, distributor=None) -> None:
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

    def _get_metrics(self, colleague_contents) -> Sequence[Mapping[str, Any]]:
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

    def _compute_content(self, raw_content, colleague_contents) -> AWSComputedContent:
        content_by_piggyback_hosts: Dict[str, List[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content) -> List[AWSSectionResult]:
        return [AWSSectionResult("", rows) for _id, rows in computed_content.content.items()]


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
    def __init__(self, hostname, session, debug=False, config=None):
        self._hostname = hostname
        self._session = session
        self._debug = debug
        self._sections = []
        self.config = config

    @abc.abstractmethod
    def init_sections(self, services, region, config, s3_limits_distributor=None):
        pass

    def _init_client(self, client_key):
        try:
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
            # during we execute an operation, eg. cloudwatch.get_metrics(**kwargs):
            # - botocore.exceptions.EndpointConnectionError
            logging.info("Invalid region name or client key %s: %s", client_key, e)
            raise

    def run(self, use_cache=True):
        exceptions = []
        results: Dict[Tuple[str, float, float], str] = {}
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
        self._write_section_results(results)

    def _write_exceptions(self, exceptions):
        sys.stdout.write("<<<aws_exceptions>>>\n")
        if exceptions:
            out = "\n".join([e.message for e in exceptions])
        else:
            out = "No exceptions"
        sys.stdout.write("%s: %s\n" % (self.__class__.__name__, out))

    def _write_section_results(self, results):
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
                cached_suffix = ":cached(%s,%s)" % (
                    int(cache_timestamp),
                    int(section_interval + 60),
                )

            if any(r.content for r in result):
                self._write_section_result(section_name, cached_suffix, result)

    def _write_section_result(self, section_name, cached_suffix, result):
        if section_name.endswith("labels"):
            section_header = "<<<%s:sep(0)%s>>>\n" % (section_name, cached_suffix)
        else:
            section_header = "<<<aws_%s%s>>>\n" % (section_name, cached_suffix)

        for row in result:
            write_piggyback_header = (
                row.piggyback_hostname and row.piggyback_hostname != self._hostname
            )
            if write_piggyback_header:
                sys.stdout.write("<<<<%s>>>>\n" % row.piggyback_hostname)
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

    def init_sections(self, services, region, config, s3_limits_distributor=None):
        if "ce" in services:
            self._sections.append(CostsAndUsage(self._init_client("ce"), region, config))

        cloudwatch_client = self._init_client("cloudwatch")
        if "wafv2" in services and config.service_config["wafv2_cloudfront"]:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits_distributor = ResultDistributor()
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "CLOUDFRONT", distributor=wafv2_limits_distributor
            )
            wafv2_summary_distributor = ResultDistributor()
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "CLOUDFRONT", distributor=wafv2_summary_distributor
            )
            wafv2_limits_distributor.add(wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, False)
            wafv2_summary_distributor.add(wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "route53" in services:
            route53_client = self._init_client("route53")
            route53_health_checks, route53_cloudwatch = _create_route53_sections(
                route53_client,
                cloudwatch_client,
                region,
                config,
            )
            self._sections.append(route53_health_checks)
            self._sections.append(route53_cloudwatch)


def _create_lamdba_sections(
    lambda_client, cloudwatch_client, cloudwatch_logs_client, region: str, config: AWSConfig
) -> Tuple[
    LambdaRegionLimits,
    LambdaSummary,
    LambdaProvisionedConcurrency,
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
]:
    lambda_limits_distributor = ResultDistributor()
    lambda_limits = LambdaRegionLimits(
        lambda_client, region, config, distributor=lambda_limits_distributor
    )
    lambda_summary_distributor = ResultDistributor()
    lambda_summary = LambdaSummary(
        lambda_client,
        region,
        config,
        lambda_summary_distributor,
    )
    lambda_limits_distributor.add(lambda_summary)
    lambda_provisioned_concurrency_configuration_distributor = ResultDistributor()
    lambda_provisioned_concurrency_configuration = LambdaProvisionedConcurrency(
        lambda_client,
        region,
        config,
        lambda_provisioned_concurrency_configuration_distributor,
    )
    lambda_summary_distributor.add(lambda_provisioned_concurrency_configuration)
    lambda_cloudwatch = LambdaCloudwatch(cloudwatch_client, region, config)
    lambda_provisioned_concurrency_configuration_distributor.add(lambda_cloudwatch)
    lambda_cloudwatch_insights = LambdaCloudwatchInsights(
        cloudwatch_logs_client,
        region,
        config,
        lambda_provisioned_concurrency_configuration_distributor,
    )
    lambda_provisioned_concurrency_configuration_distributor.add(lambda_cloudwatch_insights)
    lambda_limits_distributor = ResultDistributor()
    lambda_summary_distributor = ResultDistributor()
    lambda_provisioned_concurrency_configuration_distributor = ResultDistributor()

    lambda_limits = LambdaRegionLimits(
        lambda_client, region, config, distributor=lambda_limits_distributor
    )

    return (
        lambda_limits,
        lambda_summary,
        lambda_provisioned_concurrency_configuration,
        lambda_cloudwatch,
        lambda_cloudwatch_insights,
    )


def _create_route53_sections(
    route53_client, cloudwatch_client, region: str, config: AWSConfig
) -> Tuple[Route53HealthChecks, Route53Cloudwatch]:
    route53_distributor = ResultDistributor()
    route53_health_checks = Route53HealthChecks(route53_client, region, config, route53_distributor)
    route53_cloudwatch = Route53Cloudwatch(cloudwatch_client, region, config, distributor=None)
    route53_distributor.add(route53_cloudwatch)
    return route53_health_checks, route53_cloudwatch


class AWSSectionsGeneric(AWSSections):
    def init_sections(self, services, region, config, s3_limits_distributor=None):
        assert (
            s3_limits_distributor is not None
        ), "AWSSectionsGeneric.init_sections: Must provide s3_limits_distributor"
        assert isinstance(
            s3_limits_distributor, ResultDistributorS3Limits
        ), "AWSSectionsGeneric.init_sections: s3_limits_distributor should be an instance of ResultDistributorS3Limits"

        cloudwatch_client = self._init_client("cloudwatch")
        ec2_client = self._init_client("ec2")
        ebs_summary_distributor = ResultDistributor()
        ebs_summary = EBSSummary(ec2_client, region, config, ebs_summary_distributor)

        if "ec2" in services:
            ec2_summary_distributor = ResultDistributor()
            ec2_summary = EC2Summary(ec2_client, region, config, ec2_summary_distributor)
            ec2_labels = EC2Labels(ec2_client, region, config)
            ec2_security_groups = EC2SecurityGroups(ec2_client, region, config)
            ec2 = EC2(cloudwatch_client, region, config)
            ec2_limits_distributor = ResultDistributor()
            ec2_limits_distributor.add(ec2_summary)
            ec2_summary_distributor.add(ec2_labels)
            ec2_summary_distributor.add(ec2_security_groups)
            ec2_summary_distributor.add(ec2)
            ec2_summary_distributor.add(ebs_summary)
            if config.service_config.get("ec2_limits"):
                self._sections.append(
                    EC2Limits(
                        ec2_client,
                        region,
                        config,
                        ec2_limits_distributor,
                        self._init_client("service-quotas"),
                    )
                )
            self._sections.append(ec2_summary)
            self._sections.append(ec2_labels)
            self._sections.append(ec2_security_groups)
            self._sections.append(ec2)

        if "ebs" in services:
            ebs = EBS(cloudwatch_client, region, config)
            ebs_limits_distributor = ResultDistributor()
            ebs_limits_distributor.add(ebs_summary)
            ebs_summary_distributor.add(ebs)
            if config.service_config.get("ebs_limits"):
                self._sections.append(EBSLimits(ec2_client, region, config, ebs_limits_distributor))
            self._sections.append(ebs_summary)
            self._sections.append(ebs)

        if "elb" in services:
            elb_client = self._init_client("elb")
            elb_limits_distributor = ResultDistributor()
            elb_labels = ELBLabelsGeneric(elb_client, region, config, resource="elb")
            elb_health = ELBHealth(elb_client, region, config)
            elb = ELB(cloudwatch_client, region, config)
            elb_summary_distributor = ResultDistributor()
            elb_summary = ELBSummaryGeneric(
                elb_client, region, config, elb_summary_distributor, resource="elb"
            )
            elb_limits_distributor.add(elb_summary)
            elb_summary_distributor.add(elb_labels)
            elb_summary_distributor.add(elb_health)
            elb_summary_distributor.add(elb)
            if config.service_config.get("elb_limits"):
                self._sections.append(ELBLimits(elb_client, region, config, elb_limits_distributor))
            self._sections.append(elb_summary)
            self._sections.append(elb_labels)
            self._sections.append(elb_health)
            self._sections.append(elb)

        if "elbv2" in services:
            elbv2_client = self._init_client("elbv2")
            elbv2_limits_distributor = ResultDistributor()
            elbv2_limits = ELBv2Limits(elbv2_client, region, config, elbv2_limits_distributor)
            elbv2_summary_distributor = ResultDistributor()
            elbv2_summary = ELBSummaryGeneric(
                elbv2_client, region, config, elbv2_summary_distributor, resource="elbv2"
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
            elbv2_limits_distributor.add(elbv2_summary)
            elbv2_summary_distributor.add(elbv2_labels)
            elbv2_summary_distributor.add(elbv2_target_groups)
            elbv2_summary_distributor.add(elbv2_application)
            elbv2_summary_distributor.add(elbv2_application_target_groups_http)
            elbv2_summary_distributor.add(elbv2_application_target_groups_lambda)
            elbv2_summary_distributor.add(elbv2_network)
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
                s3_limits: Union[None, S3Limits] = S3Limits(
                    s3_client, region, config, s3_limits_distributor
                )
            else:
                s3_limits = None
            s3_summary_distributor = ResultDistributor()
            s3_summary = S3Summary(s3_client, region, config, s3_summary_distributor)

            s3_limits_distributor.add(s3_summary)
            s3 = S3(cloudwatch_client, region, config)
            s3_summary_distributor.add(s3)
            s3_requests = S3Requests(cloudwatch_client, region, config)
            s3_summary_distributor.add(s3_requests)
            if config.service_config.get("s3_limits") and s3_limits:
                self._sections.append(s3_limits)
            self._sections.append(s3_summary)
            self._sections.append(s3)
            if config.service_config["s3_requests"]:
                self._sections.append(s3_requests)

        if "glacier" in services:
            glacier = Glacier(cloudwatch_client, region, config)
            glacier_client = self._init_client("glacier")
            glacier_limits_distributor = ResultDistributor()
            glacier_limits = GlacierLimits(
                glacier_client, region, config, glacier_limits_distributor
            )
            glacier_summary_distributor = ResultDistributor()
            glacier_summary = GlacierSummary(
                glacier_client, region, config, glacier_summary_distributor
            )
            glacier_limits_distributor.add(glacier_summary)
            glacier_summary_distributor.add(glacier)
            if config.service_config.get("glacier_limits"):
                self._sections.append(glacier_limits)
            self._sections.append(glacier_summary)
            self._sections.append(glacier)

        if "rds" in services:
            rds_client = self._init_client("rds")
            rds_summary_distributor = ResultDistributor()
            rds_summary = RDSSummary(rds_client, region, config, rds_summary_distributor)
            rds_limits = RDSLimits(rds_client, region, config)
            rds = RDS(cloudwatch_client, region, config)
            rds_summary_distributor.add(rds)
            if config.service_config.get("rds_limits"):
                self._sections.append(rds_limits)
            self._sections.append(rds_summary)
            self._sections.append(rds)

        if "cloudwatch_alarms" in services:
            cloudwatch_alarms = CloudwatchAlarms(cloudwatch_client, region, config)
            cloudwatch_alarms_limits_distributor = ResultDistributor()
            cloudwatch_alarms_limits = CloudwatchAlarmsLimits(
                cloudwatch_client, region, config, cloudwatch_alarms_limits_distributor
            )
            cloudwatch_alarms_limits_distributor.add(cloudwatch_alarms)
            if config.service_config.get("cloudwatch_alarms_limits"):
                self._sections.append(cloudwatch_alarms_limits)
            if "cloudwatch_alarms" in config.service_config:
                self._sections.append(cloudwatch_alarms)

        if "dynamodb" in services:
            dynamodb_client = self._init_client("dynamodb")
            dynamodb_limits_distributor = ResultDistributor()
            dynamodb_limits = DynamoDBLimits(
                dynamodb_client, region, config, dynamodb_limits_distributor
            )
            dynamodb_summary_distributor = ResultDistributor()
            dynamodb_summary = DynamoDBSummary(
                dynamodb_client, region, config, dynamodb_summary_distributor
            )
            dynamodb_table = DynamoDBTable(cloudwatch_client, region, config)
            dynamodb_limits_distributor.add(dynamodb_summary)
            dynamodb_summary_distributor.add(dynamodb_table)
            if config.service_config.get("dynamodb_limits"):
                self._sections.append(dynamodb_limits)
            self._sections.append(dynamodb_summary)
            self._sections.append(dynamodb_table)

        if "wafv2" in services:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits_distributor = ResultDistributor()
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "REGIONAL", distributor=wafv2_limits_distributor
            )
            wafv2_summary_distributor = ResultDistributor()
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "REGIONAL", distributor=wafv2_summary_distributor
            )
            wafv2_limits_distributor.add(wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, True)
            wafv2_summary_distributor.add(wafv2_web_acl)
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
            )
            if config.service_config.get("lambda_limits"):
                self._sections.append(lambda_limits)
            self._sections.append(lambda_summary)
            self._sections.append(lambda_provisioned_concurrency_configuration)
            self._sections.append(lambda_cloudwatch)
            self._sections.append(lambda_cloudwatch_insights)


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
]


def parse_arguments(argv):
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
    parser.add_argument("--access-key-id", help="The access key ID for your AWS account")
    parser.add_argument("--secret-access-key", help="The secret access key for your AWS account.")
    parser.add_argument("--proxy-host", help="The address of the proxy server")
    parser.add_argument("--proxy-port", help="The port of the proxy server")
    parser.add_argument("--proxy-user", help="The username for authentication of the proxy server")
    parser.add_argument(
        "--proxy-password", help="The password for authentication of the proxy server"
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
    parser.add_argument("--hostname", required=True)

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

    return parser.parse_args(argv)


def _setup_logging(opt_debug, opt_verbose):
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


def _create_session(access_key_id, secret_access_key, region):
    try:
        return boto3.session.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
    except Exception as e:
        raise AwsAccessError(e)


def _sts_assume_role(access_key_id, secret_access_key, role_arn, external_id, region):
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
        session = _create_session(access_key_id, secret_access_key, region)
        sts_client = session.client("sts")
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


def _sanitize_aws_services_params(g_aws_services, r_aws_services, r_and_g_aws_services=()):
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
    aws_service_keys: Set[str] = set()
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
    port: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    address = server_address
    authentication = ""
    if port:
        address += f":{port}"
    if username and password:
        authentication = f"{username}:{password}@"
    return f"{authentication}{address}"


def _get_credentials(args: argparse.Namespace, stdin_args: Mapping[str, str]) -> Tuple[str, str]:
    access_key_id = stdin_args.get("access_key_id") or args.access_key_id
    secret_access_key = stdin_args.get("secret_access_key") or args.secret_access_key

    if access_key_id and secret_access_key:
        return access_key_id, secret_access_key

    raise AWSAccessCredentialsError("Access credentials not set properly")


class AWSAccessCredentialsError(Exception):
    pass


def _get_proxy(args: argparse.Namespace, stdin_args: Mapping[str, str]) -> botocore.config.Config:

    if not args.proxy_host:
        return None

    proxy_user = stdin_args.get("proxy_user") or args.proxy_user
    proxy_password = stdin_args.get("proxy_password") or args.proxy_password
    return botocore.config.Config(
        proxies={
            "https": _proxy_address(
                args.proxy_host,
                args.proxy_port,
                proxy_user,
                proxy_password,
            )
        }
    )


def _configure_aws(args: argparse.Namespace, sys_argv: list) -> AWSConfig:
    aws_config = AWSConfig(args.hostname, sys_argv, (args.overall_tag_key, args.overall_tag_values))

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
    ]:
        aws_config.add_single_service_config("%s_names" % service_key, service_names)
        aws_config.add_service_tags("%s_tags" % service_key, service_tags)
        aws_config.add_single_service_config("%s_limits" % service_key, service_limits)

    for arg in ["s3_requests", "cloudwatch_alarms_limits", "cloudwatch_alarms", "wafv2_cloudfront"]:
        aws_config.add_single_service_config(arg, getattr(args, arg))

    return aws_config


def main(sys_argv=None):
    if sys_argv is None:
        cmk.utils.password_store.replace_passwords()
        sys_argv = sys.argv[1:]

    args = parse_arguments(sys_argv)
    # secrets can be passed in as a command line argument for testing,
    # BUT the standard method is to pass them via stdin so that they
    # are not accessible from outside, e.g. visible on the ps output

    stdin_args = json.loads(sys.stdin.read() or "{}")

    _setup_logging(args.debug, args.verbose)

    try:
        access_key_id, secret_access_key = _get_credentials(args, stdin_args)
    except AWSAccessCredentialsError as e:
        logging.error(e)
        return 1

    hostname = args.hostname
    proxy_config = _get_proxy(args, stdin_args)

    aws_config = _configure_aws(args, sys_argv)

    global_services, regional_services = _sanitize_aws_services_params(
        args.global_services, args.services, r_and_g_aws_services=("wafv2",)
    )

    use_cache = aws_config.is_up_to_date() and not args.no_cache
    has_exceptions = False

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

    for aws_services, aws_regions, aws_sections in [
        (global_services, ["us-east-1"], AWSSectionsUSEast),
        (regional_services, args.regions, AWSSectionsGeneric),
    ]:
        if not aws_services or not aws_regions:
            continue

        for region in aws_regions:
            try:
                if args.assume_role:
                    session = _sts_assume_role(
                        access_key_id, secret_access_key, args.role_arn, args.external_id, region
                    )
                else:
                    session = _create_session(access_key_id, secret_access_key, region)

                sections = aws_sections(hostname, session, debug=args.debug, config=proxy_config)
                sections.init_sections(
                    aws_services, region, aws_config, s3_limits_distributor=s3_limits_distributor
                )
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
    if has_exceptions:
        return 1
    return 0


class AwsAccessError(MKException):
    pass
