# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
import json
from typing import Any, Mapping, Optional, Tuple, TypedDict, Sequence, Union

from .agent_based_api.v1 import check_levels, register, render, Service, State, Result, Metric
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.aws import (
    extract_aws_metrics_by_labels,
    parse_aws,
)


@dataclass(frozen=True)
class HealthCheckConfig:
    Type: str
    Port: Optional[int] = None
    # normal health checks: either FullyQualifiedDomainName or IPAddress is present
    # aggregated health checks: FullyQualifiedDomainName and IPAddress are absent
    FullyQualifiedDomainName: Optional[str] = None
    IPAddress: Optional[str] = None

    @staticmethod
    def from_health_check(d: Mapping[str, Any]) -> "HealthCheckConfig":
        return HealthCheckConfig(
            **{
                k: v
                for k, v in d.items()
                if k in ("Port", "Type", "FullyQualifiedDomainName", "IPAddress")
            }
        )

    def description(self) -> str:
        if self.Type == "CALCULATED":
            return "Aggregated health check"
        if self.FullyQualifiedDomainName:
            return f"{self.FullyQualifiedDomainName}:{str(self.Port)}"
        return f"{self.IPAddress}:{str(self.Port)}"


Route53HealthCheckSection = Mapping[str, HealthCheckConfig]


def parse_aws_route53_health_checks(string_table: StringTable) -> Route53HealthCheckSection:
    health_check: Sequence[Mapping[str, Any]] = (
        json.loads("".join(string_table[0])) if string_table else []
    )
    return {
        health_check["Id"]: HealthCheckConfig.from_health_check(health_check["HealthCheckConfig"])
        for health_check in health_check
    }


register.agent_section(
    name="aws_route53_health_checks",
    parse_function=parse_aws_route53_health_checks,
)


@dataclass
class Route53CloudwatchMetrics:
    HealthCheckStatus: int
    ChildHealthCheckHealthyCount: Optional[float] = None
    ConnectionTime: Optional[float] = None
    HealthCheckPercentageHealthy: Optional[float] = None
    SSLHandshakeTime: Optional[float] = None
    TimeToFirstByte: Optional[float] = None

    def __post_init__(self):
        # convert timespans from milliseconds to canonical seconds
        if self.ConnectionTime:
            self.ConnectionTime /= 1000.0
        if self.SSLHandshakeTime:
            self.SSLHandshakeTime /= 1000.0
        if self.TimeToFirstByte:
            self.TimeToFirstByte /= 1000.0


Route53CloudwatchSection = Mapping[str, Route53CloudwatchMetrics]


def parse_aws_route53_cloudwatch(string_table: StringTable) -> Route53CloudwatchSection:
    parsed = parse_aws(string_table)
    metrics = extract_aws_metrics_by_labels(
        [
            "ChildHealthCheckHealthyCount",
            "ConnectionTime",
            "HealthCheckPercentageHealthy",
            "HealthCheckStatus",
            "SSLHandshakeTime",
            "TimeToFirstByte",
        ],
        parsed,
    )
    return {id_: Route53CloudwatchMetrics(**value) for id_, value in metrics.items()}


register.agent_section(
    name="aws_route53_cloudwatch",
    parse_function=parse_aws_route53_cloudwatch,
)


def discover_aws_route53(
    section_aws_route53_health_checks: Optional[Route53HealthCheckSection],
    section_aws_route53_cloudwatch: Optional[Route53CloudwatchSection],
) -> DiscoveryResult:
    if section_aws_route53_health_checks and section_aws_route53_cloudwatch:
        for id_, _health_check in section_aws_route53_health_checks.items():
            yield Service(item=id_)


class Route53Parameters(TypedDict, total=False):
    levels_connection_time: Tuple[float, float]
    levels_health_check_percentage_healthy: Tuple[float, float]
    levels_ssl_handshake_time: Tuple[float, float]
    levels_time_to_first_byte: Tuple[float, float]


def check_aws_route53(
    item: str,
    params: Route53Parameters,
    section_aws_route53_health_checks: Optional[Route53HealthCheckSection],
    section_aws_route53_cloudwatch: Optional[Route53CloudwatchSection],
):
    if not (
        section_aws_route53_health_checks
        and (health_check_config := section_aws_route53_health_checks.get(item))
        and section_aws_route53_cloudwatch
        and (metrics := section_aws_route53_cloudwatch.get(item))
    ):
        return

    yield Result(state=State.OK, summary=health_check_config.description())

    if metrics.ChildHealthCheckHealthyCount is not None:
        yield from check_levels(
            metrics.ChildHealthCheckHealthyCount,
            metric_name="aws_route53_child_health_check_healthy_count",
            label="Child health check healthy count",
        )

    if metrics.ConnectionTime is not None:
        yield from check_levels(
            metrics.ConnectionTime,
            levels_upper=params["levels_connection_time"],
            metric_name="aws_route53_connection_time",
            label="Connection time",
            render_func=render.timespan,
        )

    if metrics.HealthCheckStatus is not None:
        yield Result(
            state=State.OK if metrics.HealthCheckStatus == 1 else State.CRIT,
            summary=f"Health check status: {'OK' if metrics.HealthCheckStatus == 1 else 'CRIT'}",
        )

    if metrics.HealthCheckPercentageHealthy is not None:
        yield from check_levels(
            metrics.HealthCheckPercentageHealthy,
            levels_lower=params["levels_health_check_percentage_healthy"],
            metric_name="aws_route53_health_check_percentage_healthy",
            label="Health check percentage healthy",
            render_func=render.percent,
        )

    if metrics.SSLHandshakeTime is not None:
        yield from check_levels(
            metrics.SSLHandshakeTime,
            levels_upper=params["levels_ssl_handshake_time"],
            metric_name="aws_route53_ssl_handshake_time",
            label="SSL handshake time",
            render_func=render.timespan,
        )

    if metrics.TimeToFirstByte is not None:
        yield from check_levels(
            metrics.TimeToFirstByte,
            levels_upper=params["levels_time_to_first_byte"],
            metric_name="aws_route53_time_to_first_byte",
            label="Time to first byte",
            render_func=render.timespan,
        )


_DEFAULT_PARAMETERS: Route53Parameters = {
    "levels_connection_time": (200.0, 500.0),
    "levels_health_check_percentage_healthy": (100.0, 100.0),
    "levels_ssl_handshake_time": (400.0, 1000.0),
    "levels_time_to_first_byte": (400.0, 1000.0),
}

register.check_plugin(
    name="aws_route53",
    sections=["aws_route53_health_checks", "aws_route53_cloudwatch"],
    service_name="AWS/Route53 %s",
    discovery_function=discover_aws_route53,
    check_ruleset_name="aws_route53",
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_function=check_aws_route53,
)
