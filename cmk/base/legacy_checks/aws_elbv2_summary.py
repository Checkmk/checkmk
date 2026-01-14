#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_elb_summary_generic, parse_aws

check_info = {}


def parse_aws_elbv2_summary(string_table):
    application_lbs, network_lbs = [], []
    for row in parse_aws(string_table):
        lb_type = row.get("Type")
        if lb_type == "application":
            application_lbs.append(row)
        elif lb_type == "network":
            network_lbs.append(row)
    return application_lbs, network_lbs


def discover_aws_elbv2_summary_application(parsed):
    application_lbs, _network_lbs = parsed
    if application_lbs:
        return [(None, {})]
    return []


def check_aws_elbv2_summary_application(item, params, parsed):
    application_lbs, _network_lbs = parsed
    return check_aws_elb_summary_generic(item, params, application_lbs)


check_info["aws_elbv2_summary"] = LegacyCheckDefinition(
    name="aws_elbv2_summary",
    parse_function=parse_aws_elbv2_summary,
    service_name="AWS/ApplicationELB Summary",
    discovery_function=discover_aws_elbv2_summary_application,
    check_function=check_aws_elbv2_summary_application,
)


def discover_aws_elbv2_summary_network(parsed):
    _application_lbs, network_lbs = parsed
    if network_lbs:
        return [(None, {})]
    return []


def check_aws_elbv2_summary_network(item, params, parsed):
    _application_lbs, network_lbs = parsed
    return check_aws_elb_summary_generic(item, params, network_lbs)


check_info["aws_elbv2_summary.network"] = LegacyCheckDefinition(
    name="aws_elbv2_summary_network",
    service_name="AWS/NetworkELB Summary",
    sections=["aws_elbv2_summary"],
    discovery_function=discover_aws_elbv2_summary_network,
    check_function=check_aws_elbv2_summary_network,
)
