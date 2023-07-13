#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from typing import Any

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import AWSRegions, inventory_aws_generic, parse_aws
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import aws_rds_service_item

Section = Mapping[str, Any]


def parse_aws_rds_summary(info):
    try:
        return {
            aws_rds_service_item(instance["DBInstanceIdentifier"], instance["Region"]): instance
            for instance in parse_aws(info)
        }
    except IndexError:
        return {}


#   .--summary-------------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------'


def discover_aws_rds_summary(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_rds_summary(item, params, parsed):
    instances_by_classes: dict = {}
    for instance in parsed.values():
        instance_class = instance["DBInstanceClass"]
        instances_by_classes.setdefault(instance_class, []).append(instance)

    class_infos = []
    for instance_class, instances in instances_by_classes.items():
        class_infos.append("%s: %s" % (instance_class, len(instances)))
    yield 0, ", ".join(class_infos)


check_info["aws_rds_summary"] = LegacyCheckDefinition(
    parse_function=parse_aws_rds_summary,
    service_name="AWS/RDS Summary",
    discovery_function=discover_aws_rds_summary,
    check_function=check_aws_rds_summary,
)

# .
#   .--DB status-----------------------------------------------------------.
#   |              ____  ____        _        _                            |
#   |             |  _ \| __ )   ___| |_ __ _| |_ _   _ ___                |
#   |             | | | |  _ \  / __| __/ _` | __| | | / __|               |
#   |             | |_| | |_) | \__ \ || (_| | |_| |_| \__ \               |
#   |             |____/|____/  |___/\__\__,_|\__|\__,_|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_rds_summary_db(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    db_name = data.get("DBName")
    pre_info = ""
    if db_name is not None:
        pre_info = "[%s] " % db_name
    yield 0, "%sStatus: %s" % (pre_info, data["DBInstanceStatus"])

    multi_az = data.get("MultiAZ")
    if multi_az is not None:
        if multi_az:
            multi_az_readable = "yes"
        else:
            multi_az_readable = "no"
        yield 0, "Multi AZ: %s" % multi_az_readable

    zone = data.get("AvailabilityZone")
    if zone is not None:
        region = zone[:-1]
        zone_info = zone[-1]
        yield 0, "Availability zone: %s (%s)" % (AWSRegions[region], zone_info)


check_info["aws_rds_summary.db_status"] = LegacyCheckDefinition(
    service_name="AWS/RDS %s Info",
    sections=["aws_rds_summary"],
    discovery_function=lambda p: inventory_aws_generic(p, ["DBInstanceStatus"]),
    check_function=check_aws_rds_summary_db,
)
