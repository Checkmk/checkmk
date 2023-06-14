#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from collections.abc import Iterable

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import GenericAWSSection, parse_aws


def discover_aws_ec2_summary(section: GenericAWSSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_ec2_summary(item, params, parsed):
    instances_by_state = {}
    long_output = []
    for instance in parsed:
        instance_private_dns_name = instance["PrivateDnsName"]
        instance_id = instance["InstanceId"]
        instance_state = instance["State"]["Name"]
        instances_by_state.setdefault(instance_state, []).append(instance_id)
        long_output.append("[%s] %s: %s" % (instance_id, instance_private_dns_name, instance_state))

    yield 0, "Instances: %s" % sum(
        len(v) for v in instances_by_state.values()  # type: ignore[misc]  # expected bool?!
    )
    for instance_state, instances in instances_by_state.items():
        yield 0, "%s: %s" % (instance_state, len(instances))

    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


check_info["aws_ec2_summary"] = LegacyCheckDefinition(
    parse_function=parse_aws,
    discovery_function=discover_aws_ec2_summary,
    check_function=check_aws_ec2_summary,
    service_name="AWS/EC2 Summary",
)
