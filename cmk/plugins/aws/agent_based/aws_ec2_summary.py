#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.aws.lib import GenericAWSSection, parse_aws


def discover_aws_ec2_summary(section: GenericAWSSection) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_ec2_summary(section: Any) -> CheckResult:
    instances_by_state: dict[str, list] = {}
    for instance in section:
        instance_private_dns_name = instance["PrivateDnsName"]
        instance_id = instance["InstanceId"]
        instance_state = instance["State"]["Name"]
        instances_by_state.setdefault(instance_state, []).append(instance_id)
        yield Result(
            state=State.OK,
            notice=f"[{instance_id}] {instance_private_dns_name}: {instance_state}",
        )

    yield Result(
        state=State.OK, summary="Instances: %s" % sum(len(v) for v in instances_by_state.values())
    )
    for instance_state, instances in instances_by_state.items():
        yield Result(state=State.OK, summary=f"{instance_state}: {len(instances)}")


agent_section_aws_ec2_summary = AgentSection(
    name="aws_ec2_summary",
    parse_function=parse_aws,
)

check_plugin_aws_ec2_summary = CheckPlugin(
    name="aws_ec2_summary",
    service_name="AWS/EC2 Summary",
    discovery_function=discover_aws_ec2_summary,
    check_function=check_aws_ec2_summary,
)
