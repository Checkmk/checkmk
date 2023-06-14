#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from collections.abc import Iterable

from cmk.base.check_api import get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import inventory_aws_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import GenericAWSSection, parse_aws

AWSEBSStorageTypes = {
    "standard": "Magnetic volumes",
    "gp2": "General Purpose SSD (gp2)",
    "gp3": "General Purpose SSD (gp3)",
    "io1": "Provisioned IOPS SSD (io1)",
    "io2": "Provisioned IOPS SSD (io2)",
    "st1": "Throughput Optimized HDD",
    "sc1": "Cold HDD",
}


def parse_aws_summary(info):
    parsed = {}
    for row in parse_aws(info):
        if (vid := row["VolumeId"]) not in parsed:
            parsed[vid] = row
        inst = parsed[vid]
        type_ = row["VolumeType"]
        inst.setdefault("type_readable", AWSEBSStorageTypes.get(type_, "unknown[%s]" % type_))
    return parsed


#   .--summary-------------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------'


def discover_aws_ebs_summary(section: GenericAWSSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_ebs_summary(item, params, parsed):
    stores_by_state = {}
    stores_by_type = {}
    long_output = []
    for volume_id, row in parsed.items():
        stores_by_state.setdefault(row["State"], []).append(volume_id)
        stores_by_type.setdefault(row["VolumeType"], []).append(volume_id)
        long_output.append(
            "Volume: %s, Status: %s, Type: %s, Encrypted: %s, Creation time: %s"
            % (volume_id, row["State"], row["VolumeType"], row["Encrypted"], row["CreateTime"])
        )

    yield 0, "Stores: %s" % len(parsed)
    for state, stores in stores_by_state.items():
        yield 0, "%s: %s" % (state, len(stores))
    for type_, stores in stores_by_type.items():
        yield 0, "%s: %s" % (AWSEBSStorageTypes.get(type_, "unknown[%s]" % type_), len(stores))
    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


check_info["aws_ebs_summary"] = LegacyCheckDefinition(
    parse_function=parse_aws_summary,
    discovery_function=discover_aws_ebs_summary,
    check_function=check_aws_ebs_summary,
    service_name="AWS/EBS Summary",
)

# .
#   .--health--------------------------------------------------------------.
#   |                    _                _ _   _                          |
#   |                   | |__   ___  __ _| | |_| |__                       |
#   |                   | '_ \ / _ \/ _` | | __| '_ \                      |
#   |                   | | | |  __/ (_| | | |_| | | |                     |
#   |                   |_| |_|\___|\__,_|_|\__|_| |_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@get_parsed_item_data
def check_aws_ebs_summary_health(item, params, ebs_data):
    metrics = ebs_data["VolumeStatus"]
    ebs_status = metrics["Status"]
    yield 0 if ebs_status.lower() == "ok" else 2, "Status: %s" % ebs_status
    for row in metrics["Details"]:
        yield 0, "%s: %s" % (row["Name"], row["Status"])


check_info["aws_ebs_summary.health"] = LegacyCheckDefinition(
    discovery_function=lambda p: inventory_aws_generic(p, ["VolumeStatus"]),
    check_function=check_aws_ebs_summary_health,
    service_name="AWS/EBS Health %s",
)
