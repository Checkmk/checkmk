#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm.lib_svc import parse_ibm_svc_with_header

Section = Mapping[str, Mapping[str, str]]

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


def parse_ibm_svc_enclosure(
    string_table: StringTable,
) -> Section:
    dflt_header = _get_ibm_svc_enclosure_dflt_header(string_table)
    if dflt_header is None:
        return {}

    parsed: dict[str, Mapping[str, str]] = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        parsed.setdefault(id_, data)
    return parsed


def _try_int(value: str | None) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def check_ibm_svc_enclosure(
    item: str,
    params: Mapping[str, tuple[int, int] | bool],
    section: Section,
) -> CheckResult:
    if not (data := section.get(item)):
        return

    enclosure_status = data["status"]
    yield Result(
        state=State.OK if enclosure_status == "online" else State.CRIT,
        summary=f"Status: {enclosure_status}",
    )

    for key, label in [
        ("canisters", "canisters"),
        ("PSUs", "PSUs"),
        ("fan_modules", "fan modules"),
        ("sems", "secondary expander modules"),
    ]:
        online = _try_int(data.get(f"online_{key}"))
        total = _try_int(data.get(f"total_{key}"))
        if online is None:
            continue
        # Valid values for WATO rule value levels_lower_online_canisters are
        # False, which shall be mapped to (total, total) or (warn, crit).
        raw_param = params.get(f"levels_lower_online_{key}")
        levels_lower_typed: (
            tuple[Literal["fixed"], tuple[int, int]] | tuple[Literal["no_levels"], None]
        )
        if isinstance(raw_param, tuple):
            levels_lower_typed = ("fixed", raw_param)
        elif total is not None:
            levels_lower_typed = ("fixed", (total, total))
        else:
            levels_lower_typed = ("no_levels", None)
        for result in check_levels(
            online,
            label=f"Online {label}",
            levels_lower=levels_lower_typed,
            render_func=str,
        ):
            if isinstance(result, Result) and total is not None:
                yield Result(state=result.state, summary=f"{result.summary} of {total}")
            else:
                yield result


def discover_ibm_svc_enclosure(
    section: Section,
) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_ibm_svc_enclosure = AgentSection(
    name="ibm_svc_enclosure",
    parse_function=parse_ibm_svc_enclosure,
)


check_plugin_ibm_svc_enclosure = CheckPlugin(
    name="ibm_svc_enclosure",
    service_name="Enclosure %s",
    discovery_function=discover_ibm_svc_enclosure,
    check_function=check_ibm_svc_enclosure,
    check_ruleset_name="ibm_svc_enclosure",
    check_default_parameters={},
)

#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _get_ibm_svc_enclosure_dflt_header(info: StringTable) -> list[str] | None:
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
