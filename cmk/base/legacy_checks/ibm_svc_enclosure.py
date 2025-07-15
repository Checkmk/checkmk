#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

# Example output from agent:
# <<<ibm_svc_enclosure:sep(58)>>>
# 1:online:control:yes:0:io_grp0:2072-24C:7804037:2:2:2:2:24
# 2:online:expansion:yes:0:io_grp0:2072-24E:7804306:2:2:2:2:24
# 3:online:expansion:yes:0:io_grp0:2072-24E:7804326:2:2:2:2:24
# 4:online:expansion:yes:0:io_grp0:2072-24E:7804352:2:2:2:2:24

# After a firmware upgrade the output looked like this:
# 1:online:control:yes:0:io_grp0:2072-24C:7804037:2:2:2:2:24:0:0
# 2:online:expansion:yes:0:io_grp0:2072-24E:7804306:2:2:2:2:24:0:0
# 3:online:expansion:yes:0:io_grp0:2072-24E:7804326:2:2:2:2:24:0:0
# 4:online:expansion:yes:0:io_grp0:2072-24E:7804352:2:2:2:2:24:0:0

# FW >= 7.8
# 1:online:control:yes:0:io_grp0:2072-24C:7804037:2:2:2:2:24:0:0:0:0
# 2:online:expansion:yes:0:io_grp0:2072-24E:7804306:2:2:2:2:24:0:0:0:0
# 3:online:expansion:yes:0:io_grp0:2072-24E:7804326:2:2:2:2:24:0:0:0:0
# 4:online:expansion:yes:0:io_grp0:2072-24E:7804352:2:2:2:2:24:0:0:0:0

# The names of the columns are:
# id:status:type:managed:IO_group_id:IO_group_name:product_MTM:serial_number:total_canisters:online_canisters:total_PSUs:online_PSUs:drive_slots:total_fan_modules:online_fan_modules:total_sems:online_sems

# IBM-FLASH900
# <<<ibm_svc_enclosure:sep(58)>>>
# id:status:type:product_MTM:serial_number:total_canisters:online_canisters:online_PSUs:drive_slots
# 1:online:control:9843-AE2:6860407:2:2:2:12


def parse_ibm_svc_enclosure(string_table):
    dflt_header = _get_ibm_svc_enclosure_dflt_header(string_table)
    if dflt_header is None:
        return {}

    parsed = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        parsed.setdefault(id_, data)
    return parsed


def _try_int(string):
    try:
        return int(string)
    except (ValueError, TypeError):
        return None


def check_ibm_svc_enclosure(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if params is None:
        params = {}

    enclosure_status = data["status"]
    if enclosure_status == "online":
        status = 0
    else:
        status = 2
    yield status, "Status: %s" % enclosure_status

    for key, label in [
        ("canisters", "canisters"),
        ("PSUs", "PSUs"),
        ("fan_modules", "fan modules"),
        ("sems", "secondary expander modules"),
    ]:
        online = _try_int(data.get("online_%s" % key))
        total = _try_int(data.get("total_%s" % key))
        if online is None:
            continue
        # Valid values for WATO rule value levels_lower_online_canisters are
        # False, which shall be mapped to (total, total) or (warn, crit).
        levels_lower = params.get("levels_lower_online_%s" % key) or (total, total)
        levels = (None, None) + levels_lower
        state, infotext, _perfdata = check_levels(
            online, None, levels, human_readable_func=int, infoname="Online %s" % label
        )
        if total is not None:
            infotext += " of %s" % total
        yield state, infotext


def discover_ibm_svc_enclosure(section):
    yield from ((item, {}) for item in section)


check_info["ibm_svc_enclosure"] = LegacyCheckDefinition(
    name="ibm_svc_enclosure",
    parse_function=parse_ibm_svc_enclosure,
    service_name="Enclosure %s",
    discovery_function=discover_ibm_svc_enclosure,
    check_function=check_ibm_svc_enclosure,
    check_ruleset_name="ibm_svc_enclosure",
)

#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _get_ibm_svc_enclosure_dflt_header(info):
    try:
        first_line = info[0]
    except IndexError:
        return None

    if len(first_line) == 9:
        return [
            "id",
            "status",
            "type",
            "product_MTM",
            "serial_number",
            "total_canisters",
            "online_canisters",
            "online_PSUs",
            "drive_slots",
        ]
    if len(first_line) == 13:
        return [
            "id",
            "status",
            "type",
            "managed",
            "IO_group_id",
            "IO_group_name",
            "product_MTM",
            "serial_number",
            "total_canisters",
            "online_canisters",
            "total_PSUs",
            "online_PSUs",
            "drive_slots",
        ]
    if len(first_line) == 15:
        return [
            "id",
            "status",
            "type",
            "managed",
            "IO_group_id",
            "IO_group_name",
            "product_MTM",
            "serial_number",
            "total_canisters",
            "online_canisters",
            "total_PSUs",
            "online_PSUs",
            "drive_slots",
            "total_fan_modules",
            "online_fan_modules",
        ]
    if len(first_line) == 17:
        return [
            "id",
            "status",
            "type",
            "managed",
            "IO_group_id",
            "IO_group_name",
            "product_MTM",
            "serial_number",
            "total_canisters",
            "online_canisters",
            "total_PSUs",
            "online_PSUs",
            "drive_slots",
            "total_fan_modules",
            "online_fan_modules",
            "total_sems",
            "online_sems",
        ]
    return None
