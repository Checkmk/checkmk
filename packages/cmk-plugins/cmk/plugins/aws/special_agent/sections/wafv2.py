#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any, Literal, override

from botocore.client import BaseClient

from ..config import AWSConfig, Tags
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    Dimension,
    hostname_from_name_and_region,
    Metrics,
    ResultDistributor,
)

Scope = Literal["REGIONAL", "CLOUDFRONT"]


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
    @override
    def name(self) -> str:
        return "wafv2_limits"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
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

    @override
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
                hostname_from_name_and_region(web_acl["Name"], self._region_report),
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
    @override
    def name(self) -> str:
        return "wafv2_summary"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("wafv2_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
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
        return any(tag in self._tags for tag in tagging)

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, str] = {}
        for web_acl in raw_content.content:
            content_by_piggyback_hosts.setdefault(
                hostname_from_name_and_region(web_acl["Name"], self._region_report), web_acl
            )
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
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
    @override
    def name(self) -> str:
        return "wafv2_web_acl"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("wafv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
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

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[dict[str, object]]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]
