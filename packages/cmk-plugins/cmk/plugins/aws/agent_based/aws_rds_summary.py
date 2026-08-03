#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
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
from cmk.plugins.aws.constants import AWS_REGIONS
from cmk.plugins.aws.lib import aws_rds_service_item, discover_aws_generic, parse_aws

Section = Mapping[str, Any]

_REGIONS: Mapping[str, str] = dict(AWS_REGIONS)


def parse_aws_rds_summary(string_table: StringTable) -> Section:
    try:
        return {
            aws_rds_service_item(instance["DBInstanceIdentifier"], instance["Region"]): instance
            for instance in parse_aws(string_table)
        }
    except IndexError:
        return {}


def discover_aws_rds_summary(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_rds_summary(section: Section) -> CheckResult:
    instances_by_classes: dict[str, list[Any]] = {}
    for instance in section.values():
        instance_class = instance["DBInstanceClass"]
        instances_by_classes.setdefault(instance_class, []).append(instance)

    class_infos = [
        f"{instance_class}: {len(instances)}"
        for instance_class, instances in instances_by_classes.items()
    ]
    yield Result(state=State.OK, summary=", ".join(class_infos))


agent_section_aws_rds_summary = AgentSection(
    name="aws_rds_summary",
    parse_function=parse_aws_rds_summary,
)


check_plugin_aws_rds_summary = CheckPlugin(
    name="aws_rds_summary",
    service_name="AWS/RDS Summary",
    discovery_function=discover_aws_rds_summary,
    check_function=check_aws_rds_summary,
)


def check_aws_rds_summary_db(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    pre_info = ""
    if (db_name := data.get("DBName")) is not None:
        pre_info = f"[{db_name}] "
    yield Result(state=State.OK, summary=f"{pre_info}Status: {data['DBInstanceStatus']}")

    if (multi_az := data.get("MultiAZ")) is not None:
        multi_az_readable = "yes" if multi_az else "no"
        yield Result(state=State.OK, summary=f"Multi AZ: {multi_az_readable}")

    if (zone := data.get("AvailabilityZone")) is not None:
        region = zone[:-1]
        zone_info = zone[-1]
        yield Result(state=State.OK, summary=f"Availability zone: {_REGIONS[region]} ({zone_info})")


def discover_aws_rds_summary_db_status(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(section, ["DBInstanceStatus"])


check_plugin_aws_rds_summary_db_status = CheckPlugin(
    name="aws_rds_summary_db_status",
    service_name="AWS/RDS %s Info",
    sections=["aws_rds_summary"],
    discovery_function=discover_aws_rds_summary_db_status,
    check_function=check_aws_rds_summary_db,
)
