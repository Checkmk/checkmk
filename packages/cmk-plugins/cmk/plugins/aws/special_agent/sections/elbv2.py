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

from collections.abc import Sequence
from typing import override

from botocore.client import BaseClient

from ..config import AWSConfig
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    Metrics,
    ResultDistributor,
)

LoadBalancers = dict[str, list[tuple[str, Sequence[str]]]]


def _elbv2_load_balancer_arn_to_dim(arn: str) -> str:
    # for application load balancers:
    # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/load-balancer-name/load-balancer-id
    # We need: app/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
    # for network load balancers:
    # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/net/load-balancer-name/load-balancer-id
    # We need: net/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
    return "/".join(arn.split("/")[-3:])


def _elbv2_target_group_arn_to_dim(arn: str) -> str:
    return arn.rsplit(":", maxsplit=1)[-1]


class ELBv2Limits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "elbv2_limits"

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

    @override
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
    @override
    def name(self) -> str:
        return "elbv2_target_groups"

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
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
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


class ELBv2Application(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "elbv2_application"

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
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
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
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
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

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[object]] = {}
        for row in raw_content.content:
            load_bal_dns, target_group_name = row["Label"].split(self._separator)
            row["Label"] = target_group_name
            content_by_piggyback_hosts.setdefault(load_bal_dns, []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class ELBv2ApplicationTargetGroupsHTTP(ELBv2ApplicationTargetGroupsResponses):
    @property
    @override
    def name(self) -> str:
        return "elbv2_application_target_groups_http"

    @override
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
    @override
    def name(self) -> str:
        return "elbv2_application_target_groups_lambda"

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        return self._get_metrics_with_specs(
            colleague_contents, ["lambda"], ["RequestCount", "LambdaUserError"]
        )


class ELBv2Network(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "elbv2_network"

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
        colleague = self._received_results.get("elbv2_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
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
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]
