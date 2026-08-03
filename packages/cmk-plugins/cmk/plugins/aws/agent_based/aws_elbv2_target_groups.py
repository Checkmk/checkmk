#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import parse_aws

Section = tuple[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]]


def parse_aws_elbv2_target_groups(string_table: StringTable) -> Section:
    application_target_groups: list[Mapping[str, Any]] = []
    network_target_groups: list[Mapping[str, Any]] = []
    for load_balancer_type, target_groups in parse_aws(string_table):
        if load_balancer_type == "application":
            application_target_groups.extend(target_groups)
        elif load_balancer_type == "network":
            network_target_groups.extend(target_groups)
    return application_target_groups, network_target_groups


def check_aws_elbv2_target_groups(target_groups: Sequence[Mapping[str, Any]]) -> CheckResult:
    if len(target_groups) == 0:
        raise IgnoreResultsError("Currently no data from AWS")

    target_groups_by_state: dict[str, list[Mapping[str, Any]]] = {}
    for target_group in target_groups:
        for target_health in target_group.get("TargetHealthDescriptions", []):
            target_groups_by_state.setdefault(
                target_health.get("TargetHealth", {}).get("State", "unknown"), []
            ).append(target_group)

    for state_readable, groups in target_groups_by_state.items():
        if state_readable in ("initial", "healthy", "unused", "draining", "unavailable"):
            state = State.OK
        elif state_readable == "unhealthy":
            state = State.CRIT
        else:
            state = State.UNKNOWN
        yield Result(state=state, summary=f"{state_readable} ({len(groups)})")


def discover_aws_application_elb_target_groups(section: Section) -> DiscoveryResult:
    application_target_groups, _network_target_groups = section
    if application_target_groups:
        yield Service()


def check_aws_application_elb_target_groups(section: Section) -> CheckResult:
    application_target_groups, _network_target_groups = section
    yield from check_aws_elbv2_target_groups(application_target_groups)


agent_section_aws_elbv2_target_groups = AgentSection(
    name="aws_elbv2_target_groups",
    parse_function=parse_aws_elbv2_target_groups,
)


check_plugin_aws_elbv2_target_groups = CheckPlugin(
    name="aws_elbv2_target_groups",
    service_name="AWS/ApplicationELB Target Groups",
    discovery_function=discover_aws_application_elb_target_groups,
    check_function=check_aws_application_elb_target_groups,
)


def discover_aws_network_elb_target_groups(section: Section) -> DiscoveryResult:
    _application_target_groups, network_target_groups = section
    if network_target_groups:
        yield Service()


def check_aws_network_elb_target_groups(section: Section) -> CheckResult:
    _application_target_groups, network_target_groups = section
    yield from check_aws_elbv2_target_groups(network_target_groups)


check_plugin_aws_elbv2_target_groups_network = CheckPlugin(
    name="aws_elbv2_target_groups_network",
    service_name="AWS/NetworkELB Target Groups",
    sections=["aws_elbv2_target_groups"],
    discovery_function=discover_aws_network_elb_target_groups,
    check_function=check_aws_network_elb_target_groups,
)
