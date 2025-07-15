#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.filerdisks import (
    check_filer_disks,
    FILER_DISKS_CHECK_DEFAULT_PARAMETERS,
)
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

# Agent output:
# <<<ibm_svc_disk:sep(58)>>>
# 0:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:4:1:24::
# 1:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:3:1:23::
# 2:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:2:1:22::
# 3:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:1:1:21::
# 4:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:0:1:20::
# 5:online::member:sas_hdd:558.4GB:8:V7BRZ_mdisk09:4:5:4::
# 6:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:6:1:18::
# 7:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:5:1:17::
# 8:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:4:1:16::
# 9:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:3:1:15::
# 10:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:2:1:14::
# 11:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:1:1:13::
# 12:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:0:1:12::
# 13:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:6:1:10::
# 14:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:7:1:11::
# 15:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:5:1:9::
# 16:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:3:1:7::
# 17:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:4:1:8::
# 18:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:2:1:6::
# 19:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:1:1:5::

# newer versions report an additional column
# 0:online::member:sas_hdd:558.4GB:7:V7RZ_mdisk8:4:1:24:::inactive
# 1:online::member:sas_hdd:558.4GB:7:V7RZ_mdisk8:3:1:23:::inactive

Section = Sequence


def parse_ibm_svc_disks(string_table):
    dflt_header = [
        "id",
        "status",
        "error_sequence_number",
        "use",
        "tech_type",
        "capacity",
        "mdisk_id",
        "mdisk_name",
        "member_id",
        "enclosure_id",
        "slot_id",
        "auto_manage",
        "drive_class_id",
    ]
    parsed = []
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        parsed.extend(rows)
    return parsed


def discover_ibm_svc_disks(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_ibm_svc_disks(_no_item, params, parsed):
    disks = []
    for data in parsed:
        status = data["status"]
        use = data["use"]
        capacity = data["capacity"]

        disk: dict[str, str | float] = {}
        disk["identifier"] = "Enclosure: {}, Slot: {}, Type: {}".format(
            data["enclosure_id"],
            data["slot_id"],
            data["tech_type"],
        )

        if capacity.endswith("GB"):
            disk["capacity"] = float(capacity[:-2]) * 1024 * 1024 * 1024
        elif capacity.endswith("TB"):
            disk["capacity"] = float(capacity[:-2]) * 1024 * 1024 * 1024 * 1024
        elif capacity.endswith("PB"):
            disk["capacity"] = float(capacity[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024

        # Failure State can be found here, also spare is a state here
        disk["state"] = use
        if status == "offline" and use != "failed":
            disk["state"] = "offline"

        disk["type"] = ""  # We dont have a type

        disks.append(disk)

    return check_filer_disks(disks, params)


check_info["ibm_svc_disks"] = LegacyCheckDefinition(
    name="ibm_svc_disks",
    parse_function=parse_ibm_svc_disks,
    service_name="Disk Summary",
    discovery_function=discover_ibm_svc_disks,
    check_function=check_ibm_svc_disks,
    check_ruleset_name="netapp_disks",
    check_default_parameters=FILER_DISKS_CHECK_DEFAULT_PARAMETERS,
)
