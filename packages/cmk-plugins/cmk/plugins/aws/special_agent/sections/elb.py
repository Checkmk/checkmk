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

from collections.abc import Mapping, Sequence
from typing import override

from botocore.client import BaseClient

from ..config import AWSConfig, Tags
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLabels,
    AWSSectionLimits,
    AWSSectionResult,
    Metrics,
    ResultDistributor,
)


class ELBLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "elb_limits"

    @property
    @override
    def cache_interval(self) -> int:
        # If you change this, you might have to adjust the defaults for 'levels_spillover' in checks/aws_elb
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

    @override
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
    @override
    def name(self) -> str:
        return "%s_summary" % self._resource

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
        colleague = self._received_results.get("%s_limits" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
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
        return any(tag in self._tags for tag in tagging)

    @override
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

    @override
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
    @override
    def name(self) -> str:
        return "%s_generic_labels" % self._resource

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
        colleague = self._received_results.get("%s_summary" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> object:
        (colleague_contents,) = args
        return colleague_contents.content

    @override
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
    @override
    def name(self) -> str:
        return "elb_health"

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
        colleague = self._received_results.get("elb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
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

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.items()
        ]


class ELB(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "elb"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @property
    def host_labels(self) -> Mapping[str, str]:
        return {"cmk/aws/service": "elb"}

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("elb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
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

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows, self.host_labels)
            for piggyback_hostname, rows in computed_content.content.items()
        ]
