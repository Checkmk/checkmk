#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import typing

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree
from cmk.plugins.hp_proliant.lib import DETECT, sanitize_item

check_info = {}


class HpProRaid(typing.NamedTuple):
    name: str
    status: str
    size_bytes: int
    rebuild_percent: int


def parse_hp_proliant_raid(string_table):
    parsed: dict[str, HpProRaid] = {}
    for number, name, status, size_str, rebuild in string_table:
        itemname = sanitize_item(f"{name} {number}".strip())
        parsed.setdefault(
            itemname,
            HpProRaid(
                name=itemname,
                status=status,
                size_bytes=int(size_str) * 1024 * 1024,
                rebuild_percent=int(rebuild),
            ),
        )

    return parsed


def discover_hp_proliant_raid(parsed):
    for raid in parsed:
        yield raid, None


def check_hp_proliant_raid(item, _no_params, parsed):
    map_states = {
        "1": (3, "other"),
        "2": (0, "OK"),
        "3": (2, "failed"),
        "4": (1, "unconfigured"),
        "5": (1, "recovering"),
        "6": (1, "ready for rebuild"),
        "7": (1, "rebuilding"),
        "8": (2, "wrong drive"),
        "9": (2, "bad connect"),
        "10": (2, "overheating"),
        "11": (1, "shutdown"),
        "12": (1, "automatic data expansion"),
        "13": (2, "not available"),
        "14": (1, "queued for expansion"),
        "15": (1, "multi-path access degraded"),
        "16": (1, "erasing"),
    }

    if not (raid_stats := parsed.get(item)):
        return

    state, state_readable = map_states.get(raid_stats.status, (3, "unknown"))
    yield state, f"Status: {state_readable}"
    yield 0, f"Logical volume size: {render.bytes(raid_stats.size_bytes)}"

    # From CPQIDA-MIB:
    # This value is the percent complete of the rebuild.
    # This value is only valid if the Logical Drive Status is
    # rebuilding (7) or expanding (12).
    # If the value cannot be determined or a rebuild is not active,
    # the value is set to 4,294,967,295.
    if raid_stats.status not in {"7", "12"}:
        return

    if raid_stats.rebuild_percent == 4294967295:
        yield 0, "Rebuild: undetermined"
        return

    yield 0, f"Rebuild: {render.percent(raid_stats.rebuild_percent)}"


check_info["hp_proliant_raid"] = LegacyCheckDefinition(
    name="hp_proliant_raid",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.3.2.3.1.1",
        oids=["2", "14", "4", "9", "12"],
    ),
    parse_function=parse_hp_proliant_raid,
    service_name="Logical Device %s",
    discovery_function=discover_hp_proliant_raid,
    check_function=check_hp_proliant_raid,
)
