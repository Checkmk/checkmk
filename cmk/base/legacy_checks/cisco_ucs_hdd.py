#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# comNET GmbH, Fabian Binder - 2018-05-07

from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Final, NamedTuple

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT, MAP_OPERABILITY

check_info = {}

_HOT_SPARE_VALUES: Final = {3, 4}


class HDD(NamedTuple):
    disk_id: str
    model: str
    state: int
    operability: str
    serial: str
    size: int
    vendor: str
    drive_status: int


Section = Mapping[str, HDD]


def parse_cisco_ucs_hdd(string_table: StringTable) -> Section:
    return {
        disk_id: HDD(
            disk_id,
            model,
            *MAP_OPERABILITY[r_operability],
            serial,
            int(r_size or 0) * 1024**2,
            vendor,
            int(drive_status),
        )
        for disk_id, model, r_operability, serial, r_size, vendor, drive_status in string_table
    }


def discover_cisco_ucs_hdd(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((hdd.disk_id, {}) for hdd in section.values() if hdd.operability != "removed")


def check_cisco_ucs_hdd(
    item: str, _no_params: Mapping[str, Any], section: Section
) -> Iterator[tuple[int, str]]:
    hdd = section.get(item)
    if hdd is None:
        return

    yield (
        (
            0,
            f"Status: {hdd.operability} (hot spare)",
        )
        if hdd.drive_status in _HOT_SPARE_VALUES
        else (hdd.state, f"Status: {hdd.operability}")
    )
    yield 0, f"Size: {render.disksize(hdd.size)}"
    yield 0, f"Model: {hdd.model}"
    yield 0, f"Vendor: {hdd.vendor}"
    yield 0, f"Serial number: {hdd.serial}"


check_info["cisco_ucs_hdd"] = LegacyCheckDefinition(
    name="cisco_ucs_hdd",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.45.4.1",
        oids=["6", "7", "9", "12", "13", "14", "18"],
    ),
    parse_function=parse_cisco_ucs_hdd,
    service_name="HDD %s",
    discovery_function=discover_cisco_ucs_hdd,
    check_function=check_cisco_ucs_hdd,
)
