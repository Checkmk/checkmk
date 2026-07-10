#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class Ec2SecurityGroup:
    group_id: str
    group_name: str
    description: str | None = None


def parse_aws_ec2_security_groups(string_table: StringTable) -> Sequence[Ec2SecurityGroup]:
    return [
        Ec2SecurityGroup(
            group_id=group["GroupId"],
            group_name=group["GroupName"],
            description=group.get("Description"),
        )
        for group in parse_aws(string_table)
    ]


def discover_aws_ec2_security_groups(section: Sequence[Ec2SecurityGroup]) -> DiscoveryResult:
    if section:
        yield Service(parameters={"groups": [group.group_id for group in section]})


def check_aws_ec2_security_groups(
    params: Mapping[str, Any], section: Sequence[Ec2SecurityGroup]
) -> CheckResult:
    for group in section:
        prefix = f"[{group.description}] " if group.description else ""
        infotext = f"{prefix}{group.group_name}: {group.group_id}"
        if group.group_id not in params["groups"]:
            yield Result(state=State.CRIT, summary=f"{infotext} (has changed)")
        else:
            yield Result(state=State.OK, summary=infotext)


agent_section_aws_ec2_security_groups = AgentSection(
    name="aws_ec2_security_groups",
    parse_function=parse_aws_ec2_security_groups,
)


check_plugin_aws_ec2_security_groups = CheckPlugin(
    name="aws_ec2_security_groups",
    service_name="AWS/EC2 Security Groups",
    discovery_function=discover_aws_ec2_security_groups,
    check_function=check_aws_ec2_security_groups,
    check_default_parameters={},
)
