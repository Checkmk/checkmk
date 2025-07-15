#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import inventory_aws_generic
from cmk.plugins.aws.lib import GenericAWSSection, parse_aws

check_info = {}

AWSEBSStorageTypes = {
    "standard": "Magnetic volumes",
    "gp2": "General Purpose SSD (gp2)",
    "gp3": "General Purpose SSD (gp3)",
    "io1": "Provisioned IOPS SSD (io1)",
    "io2": "Provisioned IOPS SSD (io2)",
    "st1": "Throughput Optimized HDD",
    "sc1": "Cold HDD",
}


def parse_aws_summary(string_table):
    parsed = {}
    for row in parse_aws(string_table):
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
            "Volume: {}, Status: {}, Type: {}, Encrypted: {}, Creation time: {}".format(
                volume_id, row["State"], row["VolumeType"], row["Encrypted"], row["CreateTime"]
            )
        )

    yield 0, "Stores: %s" % len(parsed)
    for state, stores in stores_by_state.items():
        yield 0, f"{state}: {len(stores)}"
    for type_, stores in stores_by_type.items():
        yield 0, "{}: {}".format(AWSEBSStorageTypes.get(type_, "unknown[%s]" % type_), len(stores))
    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


check_info["aws_ebs_summary"] = LegacyCheckDefinition(
    name="aws_ebs_summary",
    parse_function=parse_aws_summary,
    service_name="AWS/EBS Summary",
    discovery_function=discover_aws_ebs_summary,
    check_function=check_aws_ebs_summary,
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


def check_aws_ebs_summary_health(item, params, parsed):
    if not (ebs_data := parsed.get(item)):
        return
    metrics = ebs_data["VolumeStatus"]
    ebs_status = metrics["Status"]
    yield 0 if ebs_status.lower() == "ok" else 2, "Status: %s" % ebs_status
    for row in metrics["Details"]:
        yield 0, "{}: {}".format(row["Name"], row["Status"])


def discover_aws_ebs_summary_health(p):
    return inventory_aws_generic(p, ["VolumeStatus"])


check_info["aws_ebs_summary.health"] = LegacyCheckDefinition(
    name="aws_ebs_summary_health",
    service_name="AWS/EBS Health %s",
    sections=["aws_ebs_summary"],
    discovery_function=discover_aws_ebs_summary_health,
    check_function=check_aws_ebs_summary_health,
)
