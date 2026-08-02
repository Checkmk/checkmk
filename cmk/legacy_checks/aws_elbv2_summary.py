#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)
from cmk.plugins.aws.lib import (
    check_aws_elb_summary_generic,
    ELBSummaryAvailabilityZone,
    ELBSummaryLoadBalancer,
    parse_aws,
)

Section = tuple[Sequence[ELBSummaryLoadBalancer], Sequence[ELBSummaryLoadBalancer]]


def parse_aws_elbv2_summary(string_table: StringTable) -> Section:
    application_lbs: list[ELBSummaryLoadBalancer] = []
    network_lbs: list[ELBSummaryLoadBalancer] = []
    for row in parse_aws(string_table):
        load_balancer = ELBSummaryLoadBalancer(
            load_balancer_name=row["LoadBalancerName"],
            # elbv2 provides availability zones as a list of dicts including the
            # zone name.
            availability_zones=[
                ELBSummaryAvailabilityZone(zone_name=zone["ZoneName"])
                for zone in row["AvailabilityZones"]
            ],
            type=row.get("Type"),
        )
        if load_balancer.type == "application":
            application_lbs.append(load_balancer)
        elif load_balancer.type == "network":
            network_lbs.append(load_balancer)
    return application_lbs, network_lbs


def discover_aws_elbv2_summary_application(section: Section) -> DiscoveryResult:
    application_lbs, _network_lbs = section
    if application_lbs:
        yield Service()


def check_aws_elbv2_summary_application(section: Section) -> CheckResult:
    application_lbs, _network_lbs = section
    yield from check_aws_elb_summary_generic(application_lbs)


agent_section_aws_elbv2_summary = AgentSection(
    name="aws_elbv2_summary",
    parse_function=parse_aws_elbv2_summary,
)


check_plugin_aws_elbv2_summary = CheckPlugin(
    name="aws_elbv2_summary",
    service_name="AWS/ApplicationELB Summary",
    discovery_function=discover_aws_elbv2_summary_application,
    check_function=check_aws_elbv2_summary_application,
)


def discover_aws_elbv2_summary_network(section: Section) -> DiscoveryResult:
    _application_lbs, network_lbs = section
    if network_lbs:
        yield Service()


def check_aws_elbv2_summary_network(section: Section) -> CheckResult:
    _application_lbs, network_lbs = section
    yield from check_aws_elb_summary_generic(network_lbs)


check_plugin_aws_elbv2_summary_network = CheckPlugin(
    name="aws_elbv2_summary_network",
    service_name="AWS/NetworkELB Summary",
    sections=["aws_elbv2_summary"],
    discovery_function=discover_aws_elbv2_summary_network,
    check_function=check_aws_elbv2_summary_network,
)
