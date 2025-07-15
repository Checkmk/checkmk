#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.aws import parse_aws

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

AWSELBHealthMap = {
    "InService": "in service",
    "OutOfService": "out of service",
    "Unknown": "unknown",
}


def parse_aws_elb_health(string_table):
    try:
        return parse_aws(string_table)[-1]
    except IndexError:
        return {}


def discover_aws_elb_health(section):
    if section:
        yield None, {}


def check_aws_elb_health(item, params, parsed):
    state_readable = AWSELBHealthMap[parsed["State"]]
    if state_readable == "in service":
        state = 0
    elif state_readable == "out of service":
        state = 1
    else:
        state = 3
    yield state, "Status: %s" % state_readable
    yield 0, "Instance: %s" % parsed["InstanceId"]

    reason_code = parsed["ReasonCode"]
    if reason_code not in [None, "", "N/A"]:
        yield 0, "Reason: %s" % reason_code

    description = parsed["Description"]
    if description not in [None, "", "N/A"]:
        yield 0, "Description: %s" % description


check_info["aws_elb_health"] = LegacyCheckDefinition(
    name="aws_elb_health",
    parse_function=parse_aws_elb_health,
    service_name="AWS/ELB Health ",
    discovery_function=discover_aws_elb_health,
    check_function=check_aws_elb_health,
)
