#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""functions for all redfish components"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple

from cmk.agent_based.v2 import DiscoveryResult, Service, StringTable
from cmk.rulesets.v1 import Title

SectionSystem = Mapping[str, Mapping[str, Any]]

Levels = tuple[Literal["fixed"], tuple[float, float]]
RedfishAPIData = Mapping[str, Any]


@dataclass(frozen=True)
class Section:
    name: str
    title: Title


REDFISH_SECTIONS = (
    Section(name="Memory", title=Title("Memory Modules")),
    Section(name="Power", title=Title("Powers Supply")),
    Section(name="Processors", title=Title("CPUs")),
    Section(name="Thermal", title=Title("Fan and Temperatures")),
    Section(
        name="FirmwareInventory",
        title=Title("Firmware Versions"),
    ),
    Section(name="NetworkAdapters", title=Title("Network Cards")),
    Section(
        name="NetworkInterfaces",
        title=Title("Network Interfaces 1"),
    ),
    Section(
        name="EthernetInterfaces",
        title=Title("Network Interfaces 2"),
    ),
    Section(name="Storage", title=Title("Storage")),
    Section(
        name="ArrayControllers",
        title=Title("Array Controllers"),
    ),
    Section(
        name="SmartStorage",
        title=Title("HPE - Storagesubsystem"),
    ),
    Section(
        name="HostBusAdapters",
        title=Title("Hostbustadapters"),
    ),
    Section(name="PhysicalDrives", title=Title("iLO5 - Physical Drives")),
    Section(name="LogicalDrives", title=Title("iLO5 - Logical Drives")),
    Section(name="Drives", title=Title("Drives")),
    Section(name="Volumes", title=Title("Volumes")),
    Section(
        name="SimpleStorage",
        title=Title("Simple Storage Collection (tbd)"),
    ),
)


class Perfdata(NamedTuple):
    """normal monitoring performance data"""

    value: float
    levels_upper: Levels | None
    levels_lower: Levels | None
    boundaries: tuple[float | None, float | None] | None


def parse_redfish(string_table: StringTable) -> RedfishAPIData:
    """parse one line of data to dictionary"""
    try:
        return json.loads(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError):
        return {}


def parse_redfish_multiple(string_table: StringTable) -> RedfishAPIData:
    """parse list of device dictionaries to one dictionary"""
    hpe_matches = [
        "SmartStorageDiskDrive",
        "SmartStorageLogicalDrive",
    ]

    parsed: dict[str, Mapping[str, Any]] = {}
    for line in string_table:
        entry = json.loads(line[0])
        # error entry
        # {"error": "Storage data could not be fetched\n"}
        if entry.get("error"):
            continue
        if not entry.get("@odata.type"):
            continue
        if any(x in entry.get("@odata.type") for x in hpe_matches):
            item = redfish_item_hpe(entry)
        elif "Drive" in entry.get("@odata.type"):
            item = entry.get("@odata.id")
        elif "Power" in entry.get("@odata.type"):
            item = entry.get("@odata.id")
        elif "Thermal" in entry.get("@odata.type"):
            item = entry.get("@odata.id")
        else:
            item = entry.get("Id")
        parsed.setdefault(item, entry)
    return parsed


def discovery_redfish_multiple(section: RedfishAPIData) -> DiscoveryResult:
    """Discovery multiple items from one dictionary"""
    for item in section:
        yield Service(item=item)


def _try_convert_to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def redfish_item_hpe(section: RedfishAPIData) -> str:
    """Item names for HPE devices"""
    # Example
    # "/redfish/v1/Systems/1/SmartStorage/ArrayControllers/0/LogicalDrives/1/"
    # or !!!
    # "/redfish/v1/Systems/1/SmartStorage/ArrayControllers/0/LogicalDrives/1"
    hpe_types = [
        "DiskDrives",
        "LogicalDrives",
    ]
    item = ""
    logical_item = str(section["@odata.id"]).strip("/")
    logical_list = logical_item.split("/")
    if any(x in logical_list for x in hpe_types):
        item = f"{logical_list[-3]}:{logical_list[-1]}"
    return item


def redfish_health_state(state: Mapping[str, Any]) -> tuple[int, str]:
    """Transfer Redfish health to monitoring health state"""
    health_map: dict[str, tuple[int, str]] = {
        "OK": (0, "Normal"),
        "Warning": (1, "A condition requires attention."),
        "Critical": (2, "A critical condition requires immediate attention."),
    }

    state_map: dict[str, tuple[int, str]] = {
        "Enabled": (0, "This resource is enabled."),
        "Disabled": (1, "This resource is disabled."),
        "StandbyOffline": (
            1,
            "This resource is enabled but awaits an external action to activate it.",
        ),
        "StandbySpare": (
            0,
            "This resource is part of a redundancy set and awaits a \
failover or other external action to activate it.",
        ),
        "InTest": (
            0,
            "This resource is undergoing testing, or is in the process of \
capturing information for debugging.",
        ),
        "Starting": (0, "This resource is starting."),
        "Absent": (1, "This resource is either not present or detected."),
        "Updating": (1, "The element is updating and may be unavailable or degraded"),
        "UnavailableOffline": (
            1,
            "This function or resource is present but cannot be used",
        ),
        "Deferring": (
            0,
            "The element will not process any commands but will queue new requests",
        ),
        "Quiesced": (
            0,
            "The element is enabled but only processes a restricted set of commands",
        ),
        "Present": (0, "Unoffical resource state - device is present"),
    }

    dev_state = 0
    dev_msg = []
    for key in state.keys():
        state_msg = None
        temp_state = 0
        if key in ["Health"]:
            if state[key] is None:
                continue
            temp_state, state_msg = health_map.get(
                state[key], (3, f"Unknown health state: {state[key]}")
            )
            state_msg = f"Component State: {state_msg}"
        elif key == "HealthRollup":
            if state[key] is None:
                continue
            temp_state, state_msg = health_map.get(
                state[key], (3, f"Unknown rollup health state: {state[key]}")
            )
            state_msg = f"Rollup State: {state_msg}"
        elif key == "State":
            if state[key] is None:
                continue
            temp_state, state_msg = state_map.get(state[key], (3, f"Unknown state: {state[key]}"))
        dev_state = max(dev_state, temp_state)
        if state_msg:
            dev_msg.append(state_msg)

    if not dev_msg:
        dev_msg.append("No state information found")

    return dev_state, ", ".join(dev_msg)


def process_redfish_perfdata(entry: Mapping[str, Any]) -> None | Perfdata:
    """Redfish performance data to monitoring performance data"""
    value = None
    if "Reading" in entry.keys():
        value = entry.get("Reading", 0)
    elif "ReadingVolts" in entry.keys():
        value = entry.get("ReadingVolts", 0)
    elif "ReadingCelsius" in entry.keys():
        value = entry.get("ReadingCelsius", 0)
    value = _try_convert_to_float(value)
    if value is None:
        return None

    min_range = _try_convert_to_float(entry.get("MinReadingRange", None))
    max_range = _try_convert_to_float(entry.get("MaxReadingRange", None))
    min_warn = _try_convert_to_float(entry.get("LowerThresholdNonCritical", None))
    min_crit = _try_convert_to_float(entry.get("LowerThresholdCritical", None))
    upper_warn = _try_convert_to_float(entry.get("UpperThresholdNonCritical", None))
    upper_crit = _try_convert_to_float(entry.get("UpperThresholdCritical", None))

    if min_warn is None and min_crit is not None:
        min_warn = min_crit

    if upper_warn is None and upper_crit is not None:
        upper_warn = upper_crit

    if min_warn is not None and min_crit is None:
        min_crit = float("-inf")

    if upper_warn is not None and upper_crit is None:
        upper_crit = float("inf")

    def optional_tuple(warn: float | None, crit: float | None) -> Levels | None:
        assert (warn is None) == (crit is None)
        if warn is not None and crit is not None:
            return ("fixed", (warn, crit))
        return None

    return Perfdata(
        value,
        levels_upper=optional_tuple(upper_warn, upper_crit),
        levels_lower=optional_tuple(min_warn, min_crit),
        boundaries=(
            min_range,
            max_range,
        ),
    )


def find_key_recursive(d, key):
    """Search multilevel dict for key"""
    if key in d:
        return d[key]
    for _k, v in d.items():
        if isinstance(v, dict):
            value = find_key_recursive(v, key)
            if value:
                return value
    return None
