#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ipmi.lib import ipmi as ipmi_utils

_NA_VALUES = {"NA", "N/A"}


def _na_str(str_value: str) -> str:
    return "" if str_value in _NA_VALUES else str_value


def _na_float(str_value: str) -> float | None:
    return None if str_value in _NA_VALUES else float(str_value)


class Status(NamedTuple):
    txt: str
    is_ok: bool


def _parse_status_txt(status_txt: str) -> Status:
    if status_txt.startswith("[") or status_txt.startswith("'"):
        status_txt = status_txt[1:]
    if status_txt.endswith("]") or status_txt.endswith("'"):
        status_txt = status_txt[:-1]
    if status_txt in ["NA", "N/A", "Unknown"] or "_=_" in status_txt:
        return Status(txt=status_txt.replace("_", " "), is_ok=False)
    if status_txt in ["S0G0", "S0/G0"]:
        return Status(txt="System full operational, working", is_ok=True)
    return Status(txt=status_txt.replace("_", " "), is_ok=True)


def parse_ipmi_sensors(string_table: StringTable) -> ipmi_utils.Section:
    section: ipmi_utils.Section = {}

    # This function deals with several generations of ipmi-sensors output.
    # In Werk #16691 we made the output of the linux agent and the special agent
    # consistent, except for an additional header line not filtered by the linux agent.
    # For now: strip a potential header here, and deal with the output the way we did
    # before. Simplify this once we stop supporting the older agent.
    for line in string_table:
        # The string table may contain multiple header lines.
        if line[0].strip() == "ID":
            continue
        _sid, sensorname, *reading_levels_and_more, status_txt = (
            x.strip(" \n\t\x00") for x in line
        )
        status_from_text = _parse_status_txt(status_txt)
        sensorname = sensorname.replace(" ", "_")

        if not status_from_text.is_ok and sensorname not in section:
            continue

        sensor = section.setdefault(
            sensorname,
            ipmi_utils.Sensor(status_txt=status_from_text.txt, unit=""),
        )

        match reading_levels_and_more:
            case [reading_levels]:
                if "(" in reading_levels:
                    # 339 Voltage_3.3VCC 3.33_V_(NA/NA) [OK]
                    reading, levels = reading_levels[:-1].split("(")
                else:
                    # 59 M2_Temp0(PCIe1)_(Temperature) NA/79.00_41.00_C [OK]
                    levels, reading = reading_levels.split("_", 1)

                value, unit, *_ = reading.split("_")
                lower, upper = levels.split("/")

                sensor.value = _na_float(value)
                sensor.unit = _na_str(unit)
                sensor.crit_low = _na_float(lower)
                sensor.crit_high = _na_float(upper)

            case [type_, value, unit]:
                sensor.value = _na_float(value)
                sensor.unit = _na_str(unit)
                sensor.type_ = type_

            case [type_, status, value, unit]:
                sensor.state = ipmi_utils.Sensor.parse_state(status)
                sensor.value = _na_float(value)
                sensor.unit = _na_str(unit)
                sensor.type_ = type_

            case [type_, status, value, unit, _, lower_c, lower_nc, upper_nc, upper_c, _]:
                sensor.value = _na_float(value)
                sensor.unit = _na_str(unit)
                sensor.state = ipmi_utils.Sensor.parse_state(status)
                sensor.crit_low = _na_float(lower_c)
                sensor.warn_low = _na_float(lower_nc)
                sensor.warn_high = _na_float(upper_nc)
                sensor.crit_high = _na_float(upper_c)
                sensor.type_ = type_

    return section


agent_section_ipmi_sensors = AgentSection(
    name="ipmi_sensors",
    parse_function=parse_ipmi_sensors,
)


def discover_ipmi_sensors(
    params: ipmi_utils.DiscoveryParams,
    section: ipmi_utils.Section,
) -> DiscoveryResult:
    mode, ignore_params = params["discovery_mode"]

    if mode == "summarize":
        yield Service(item="Summary FreeIPMI")
        return

    yield from ipmi_utils.discover_individual_sensors(ignore_params or {}, section)


def _status_txt_mapping(status_txt: str) -> State:
    state = {
        "ok": State.OK,
        "warning": State.WARN,
        "critical": State.CRIT,
        "failed": State.CRIT,
        "unknown": State.UNKNOWN,
    }.get(status_txt.lower())
    if state is not None:
        return state

    if "non-critical" in status_txt.lower():
        return State.WARN
    if status_txt.lower().startswith("nc"):
        return State.WARN

    if (
        status_txt.lower()
        in [
            "entity present",
            "battery presence detected",
            "drive presence",
            "transition to running",
            "device enabled",
            "system full operational, working",
            "system restart",
            "present",
            "transition to ok",
        ]
        or status_txt.startswith("Fully Redundant")
        or status_txt.endswith("is connected")
        or status_txt.endswith("Presence detected")
        or status_txt.endswith("Device Present")
    ):
        return State.OK
    return State.CRIT


def check_ipmi_sensors(
    item: str,
    params: Mapping[str, Any],
    section: ipmi_utils.Section,
) -> CheckResult:
    yield from ipmi_utils.check_ipmi(
        item,
        params,
        section,
        True,
        _status_txt_mapping,
    )


check_plugin_ipmi_sensors = CheckPlugin(
    name="ipmi_sensors",
    service_name="IPMI Sensor %s",
    discovery_function=discover_ipmi_sensors,
    discovery_ruleset_name="inventory_ipmi_rules",
    discovery_default_parameters={"discovery_mode": ("single", {})},
    check_function=check_ipmi_sensors,
    check_ruleset_name="ipmi",
    check_default_parameters={},
)
