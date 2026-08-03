#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable
from cmk.legacy_includes.aws import (
    check_aws_elb_summary_generic,
    ELBSummaryAvailabilityZone,
    ELBSummaryLoadBalancer,
)
from cmk.plugins.aws.lib import parse_aws

check_info = {}

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


def discover_aws_elbv2_summary_application(parsed: Section):
    application_lbs, _network_lbs = parsed
    if application_lbs:
        return [(None, {})]
    return []


def check_aws_elbv2_summary_application(item, params, parsed: Section):
    application_lbs, _network_lbs = parsed
    return check_aws_elb_summary_generic(item, params, application_lbs)


check_info["aws_elbv2_summary"] = LegacyCheckDefinition(
    name="aws_elbv2_summary",
    parse_function=parse_aws_elbv2_summary,
    service_name="AWS/ApplicationELB Summary",
    discovery_function=discover_aws_elbv2_summary_application,
    check_function=check_aws_elbv2_summary_application,
)


def discover_aws_elbv2_summary_network(parsed: Section):
    _application_lbs, network_lbs = parsed
    if network_lbs:
        return [(None, {})]
    return []


def check_aws_elbv2_summary_network(item, params, parsed: Section):
    _application_lbs, network_lbs = parsed
    return check_aws_elb_summary_generic(item, params, network_lbs)


check_info["aws_elbv2_summary.network"] = LegacyCheckDefinition(
    name="aws_elbv2_summary_network",
    service_name="AWS/NetworkELB Summary",
    sections=["aws_elbv2_summary"],
    discovery_function=discover_aws_elbv2_summary_network,
    check_function=check_aws_elbv2_summary_network,
)
