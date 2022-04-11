#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# Slot Number: 0
# Device Id: 4
# Raw Size: 140014MB [0x11177330 Sectors]
# Firmware state: Unconfigured(good)
# Inquiry Data: FUJITSU MBB2147RC       5204BS04P9104BV5
# Slot Number: 1
# Device Id: 5
# Raw Size: 140014MB [0x11177330 Sectors]
# Firmware state: Unconfigured(good)
# Inquiry Data: FUJITSU MBB2147RC       5204BS04P9104BSC

from typing import Final, Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import megaraid

# This makes service descriptions backward compatible to match
# inventory made by older versions that didn't support multiple
# controllers
megaraid_pdisks_adapterstr = ["e", "f", "g", "h", "i", "j", "k", "l"]


_NORMALIZE_STATE: Final = {
    "Unconfigured(good)": "Unconfigured Good",
    "Unconfigured(bad)": "Unconfigured Bad",
}


_FIXED_STATES = {
    "Hotspare": 0,
    "JBOD": 0,
    "Failed": 2,
    "Copyback": 1,
    "Rebuild": 1,
}


def parse_megaraid_pdisks(string_table: StringTable) -> megaraid.SectionPDisks:
    parsed = {}
    adapters: dict[int, dict[int, int]] = {0: {}}
    current_adapter = adapters[0]
    adapter = 0
    enclosure_devid = -181
    predictive_failure_count = None
    for line in string_table:
        if line[0] == "adapter":
            current_adapter = {}
            adapters[int(line[1])] = current_adapter
        elif line[0] == "dev2enc":
            if line[2].isdigit():
                current_adapter[int(line[5])] = int(line[2])
        elif line[0] == "Adapter" and len(line) == 2:
            current_adapter = adapters[int(line[1][1:])]  # Raute weglassen
            adapter = int(line[1][1:])
        elif line[0] == "Enclosure" and line[1] == "Device":
            try:
                enclosure_devid = int(line[-1])
                # this should fix inventory problems.
                adapters[adapter][enclosure_devid] = enclosure_devid

            except Exception:  # no enclosure device
                enclosure_devid = 0
                adapters[adapter][0] = 0
        elif line[0] == "Enclosure" and line[1] == "Number:":
            for devid, number in current_adapter.items():
                if number == int(line[-1]):
                    enclosure_devid = devid
                    break

        elif line[0] == "Slot":
            slot = int(line[-1])
        elif line[0] == "Predictive" and line[1] == "Failure" and line[2] == "Count:":
            predictive_failure_count = int(line[3])
        elif line[0] == "Firmware" and line[1] == "state:":
            state = line[2].rstrip(",")
        elif line[0] == "Inquiry" and line[1] == "Data:":
            name = " ".join(line[2:])
            # Adapter, Enclosure, Encolsure Device ID, Slot, State, Name
            enclosure = adapters[adapter][enclosure_devid]
            item = f"/c{adapter}/e{enclosure}/s{slot}"

            disk = megaraid.PDisk(
                name, _NORMALIZE_STATE.get(state, state), predictive_failure_count
            )

            parsed[item] = disk
            predictive_failure_count = None

            # Add it under the old item name. Not discovered, but can be used when checking
            legacy_item = f"{megaraid_pdisks_adapterstr[adapter]}{enclosure}/{slot}"
            parsed[legacy_item] = disk

    return parsed


register.agent_section(
    name="megaraid_pdisks",
    parse_function=parse_megaraid_pdisks,
)


def discover_megaraid_pdisks(section: megaraid.SectionPDisks) -> DiscoveryResult:
    # Items changed from e.g. 'f3/2' to '/c1/e3/s2' for consistency.
    # Only discover the new-style items.
    # The old items are kept in section, so that old services using them will still produce results
    yield from (Service(item=item) for item in section if item.startswith("/c"))


def check_megaraid_pdisks(
    item: str,
    params: Mapping[str, int],
    section: megaraid.SectionPDisks,
) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    state_map = {**_FIXED_STATES, **params}
    yield Result(
        state=State(state_map.get(disk.state, 3)),
        summary=f"{disk.state.capitalize()}",
    )

    if disk.name != item:
        yield Result(state=State.OK, summary=f"Name: {disk.name}")

    if disk.failures is None:
        return

    yield Result(
        state=State.WARN if disk.failures > 0 else State.OK,
        summary=f"Predictive fail count: {disk.failures}",
    )


register.check_plugin(
    name="megaraid_pdisks",
    check_function=check_megaraid_pdisks,
    discovery_function=discover_megaraid_pdisks,
    service_name="RAID pysical disk %s",
    check_default_parameters=megaraid.PDISKS_DEFAULTS,
    check_ruleset_name="storcli_pdisks",
)
