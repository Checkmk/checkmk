#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import parse_aws

AWSELBHealthMap = {
    "InService": "in service",
    "OutOfService": "out of service",
    "Unknown": "unknown",
}


@dataclass(frozen=True)
class ElbHealth:
    state: str
    instance_id: str
    reason_code: str | None = None
    description: str | None = None


def parse_aws_elb_health(string_table: StringTable) -> ElbHealth | None:
    try:
        row = parse_aws(string_table)[-1]
    except IndexError:
        return None
    return ElbHealth(
        state=row["State"],
        instance_id=row["InstanceId"],
        reason_code=row.get("ReasonCode"),
        description=row.get("Description"),
    )


def discover_aws_elb_health(section: ElbHealth | None) -> DiscoveryResult:
    if section is not None:
        yield Service()


def check_aws_elb_health(section: ElbHealth | None) -> CheckResult:
    if section is None:
        return
    state_readable = AWSELBHealthMap[section.state]
    if state_readable == "in service":
        state = State.OK
    elif state_readable == "out of service":
        state = State.WARN
    else:
        state = State.UNKNOWN
    yield Result(state=state, summary=f"Status: {state_readable}")
    yield Result(state=State.OK, summary=f"Instance: {section.instance_id}")

    if section.reason_code not in [None, "", "N/A"]:
        yield Result(state=State.OK, summary=f"Reason: {section.reason_code}")

    if section.description not in [None, "", "N/A"]:
        yield Result(state=State.OK, summary=f"Description: {section.description}")


agent_section_aws_elb_health = AgentSection(
    name="aws_elb_health",
    parse_function=parse_aws_elb_health,
)


check_plugin_aws_elb_health = CheckPlugin(
    name="aws_elb_health",
    service_name="AWS/ELB Health ",
    discovery_function=discover_aws_elb_health,
    check_function=check_aws_elb_health,
)
