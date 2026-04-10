#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# APC NetShelter Advanced Rack PDU (APDU series)
# MIB reference: mibs/APC-CPDU-v1_9-MIB.txt
#
# Device:
# .1.3.6.1.4.1.318.1.1.32.2.2.1.2   "mypdu"     - device name
# .1.3.6.1.4.1.318.1.1.32.2.3.1.13  "43.5kVA"   - rated power (DisplayString)
# .1.3.6.1.4.1.318.1.1.32.2.4.1.4   4583        - device active power (watts)
# .1.3.6.1.4.1.318.1.1.32.2.4.1.5   4605        - device apparent power (VA)
#
# Phases:
# .1.3.6.1.4.1.318.1.1.32.3.1       3           - number of phases (scalar)
# .1.3.6.1.4.1.318.1.1.32.3.4.1.1   1           - phase index
# .1.3.6.1.4.1.318.1.1.32.3.4.1.3   5           - current state (5=normal)
# .1.3.6.1.4.1.318.1.1.32.3.4.1.5   620         - current (hundredths of Amps)
# .1.3.6.1.4.1.318.1.1.32.3.4.1.7   1431        - active power (watts)
#
# Phase thresholds (device-reported):
# .1.3.6.1.4.1.318.1.1.32.3.2.1.1   1           - phase config index
# .1.3.6.1.4.1.318.1.1.32.3.2.1.6   5700        - upper critical current (hundredths of Amps)
# .1.3.6.1.4.1.318.1.1.32.3.2.1.7   4500        - upper warning current (hundredths of Amps)
#
# Banks:
# .1.3.6.1.4.1.318.1.1.32.4.4.1.3   "B1"        - bank name
# .1.3.6.1.4.1.318.1.1.32.4.4.1.4   5           - bank load state
# .1.3.6.1.4.1.318.1.1.32.4.4.1.5   231         - bank current (hundredths of Amps)

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

_STATE_MAP: Mapping[str, tuple[State, str]] = {
    "1": (State.CRIT, "upper critical"),
    "2": (State.WARN, "upper warning"),
    "3": (State.WARN, "lower warning"),
    "4": (State.CRIT, "lower critical"),
    "5": (State.OK, "normal"),
}


@dataclass(frozen=True, kw_only=True)
class CurrentReading:
    value: float
    state: State = State.OK
    state_text: str = ""


@dataclass(frozen=True, kw_only=True)
class NetShelterPDUItem:
    current: CurrentReading | None = None
    power: float | None = None
    output_load: float | None = None
    warn_current: float | None = None
    crit_current: float | None = None


type Section = Mapping[str, NetShelterPDUItem]

DETECT_APC_NETSHELTERPDU = startswith(
    ".1.3.6.1.2.1.1.2.0",
    ".1.3.6.1.4.1.318.1.1.32",
)


def _current_reading(amperage_str: str, device_state: str) -> CurrentReading:
    state, state_text = _STATE_MAP.get(device_state, (State.CRIT, "unknown state"))
    return CurrentReading(
        value=float(amperage_str) / 100,
        state=state,
        state_text=state_text,
    )


def _parse_rated_va(rated_power_str: str) -> float | None:
    """Parse rated power string like '43.5kVA' into VA."""
    if match := re.match(r"([\d.]+)\s*kVA", rated_power_str, re.IGNORECASE):
        return float(match.group(1)) * 1000
    if match := re.match(r"([\d.]+)\s*VA", rated_power_str, re.IGNORECASE):
        return float(match.group(1))
    return None


def parse_apc_netshelterpdu_power(string_table: Sequence[StringTable]) -> Section | None:
    if not any(string_table):
        return None

    parsed = dict[str, NetShelterPDUItem]()
    (
        device_info,
        device_status,
        n_phases,
        phase_status,
        bank_status,
        phase_config,
        device_properties,
    ) = string_table

    # Build threshold map from phase config table (device-reported WARN/CRIT)
    # Entry 6 = upper critical, entry 7 = upper warning, both in hundredths of Amps
    phase_thresholds: dict[str, tuple[float, float]] = {}
    for phase_index, upper_crit_str, upper_warn_str in phase_config:
        phase_thresholds[phase_index] = (
            float(upper_warn_str) / 100,
            float(upper_crit_str) / 100,
        )

    # Rated capacity for total load calculation
    rated_va = _parse_rated_va(device_properties[0][0]) if device_properties else None

    # Device level: name + total power + load percentage
    device_name = None
    if device_info and device_status:
        pdu_name = device_info[0][0]
        device_power = float(device_status[0][0])
        apparent_power = float(device_status[0][1])
        device_name = f"Device {pdu_name}"

        # Calculate total load as apparent power / rated VA
        # rated_va is None for unparseable strings and 0.0 for "0kVA" — both skip division
        output_load = (
            apparent_power / rated_va * 100 if rated_va is not None and rated_va > 0 else None
        )

        # Single-phase PDU: also show current on Device item
        current = (
            _current_reading(phase_status[0][2], phase_status[0][1])
            if n_phases and n_phases[0][0] == "1" and phase_status
            else None
        )
        parsed[device_name] = NetShelterPDUItem(
            power=device_power,
            current=current,
            output_load=output_load,
        )

    # Phase level: per-phase current + power + device thresholds
    for phase_index, phase_state, phase_current, phase_power in phase_status:
        warn, crit = phase_thresholds.get(phase_index, (None, None))
        parsed[f"Phase {phase_index}"] = NetShelterPDUItem(
            current=_current_reading(phase_current, phase_state),
            power=float(phase_power),
            warn_current=warn,
            crit_current=crit,
        )

    # Bank level: per-bank current
    for bank_name, bank_state, bank_current in bank_status:
        if bank_name == "NA":
            continue
        parsed[f"Bank {bank_name}"] = NetShelterPDUItem(
            current=_current_reading(bank_current, bank_state),
        )

    return parsed or None


snmp_section_apc_netshelterpdu_power = SNMPSection(
    name="apc_netshelterpdu_power",
    parse_function=parse_apc_netshelterpdu_power,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.2.2.1",
            oids=[
                "2",  # device name
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.2.4.1",
            oids=[
                "4",  # device active power (watts)
                "5",  # device apparent power (VA)
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.3",
            oids=[
                "1",  # number of phases
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.3.4.1",
            oids=[
                "1",  # phase index
                "3",  # current state (5=normal)
                "5",  # current (hundredths of Amps)
                "7",  # active power (watts)
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.4.4.1",
            oids=[
                "3",  # bank name
                "4",  # bank load state
                "5",  # bank current (hundredths of Amps)
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.3.2.1",
            oids=[
                "1",  # phase index
                "6",  # upper critical current threshold (hundredths of Amps)
                "7",  # upper warning current threshold (hundredths of Amps)
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.2.3.1",
            oids=[
                "13",  # pduUnitPropertiesRatedPower (DisplayString, e.g. "43.5kVA")
            ],
        ),
    ],
    detect=DETECT_APC_NETSHELTERPDU,
)


def discover_apc_netshelterpdu_power(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_apc_netshelterpdu_power(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (entry := section.get(item)) is None:
        return

    if entry.current is not None:
        # Determine current thresholds: user params > device-reported > none
        current_levels = params.get("current")
        if (
            current_levels is None
            and entry.warn_current is not None
            and entry.crit_current is not None
        ):
            current_levels = (entry.warn_current, entry.crit_current)

        yield from check_levels(
            entry.current.value,
            metric_name="current",
            levels_upper=("fixed", current_levels) if current_levels else None,
            render_func=lambda v: f"{v:.1f} A",
            label="Current",
        )
        if entry.current.state_text:
            yield Result(state=entry.current.state, summary=entry.current.state_text)

    if entry.output_load is not None:
        load_levels = params.get("output_load")
        if load_levels is None:
            load_levels = (80, 90)

        yield from check_levels(
            entry.output_load,
            metric_name="output_load",
            levels_upper=("fixed", load_levels) if load_levels else None,
            render_func=render.percent,
            label="Load",
        )

    if entry.power is not None:
        yield from check_levels(
            entry.power,
            metric_name="power",
            levels_upper=("fixed", params["power"]) if "power" in params else None,
            render_func=lambda v: f"{v:.1f} W",
            label="Power",
        )


check_plugin_apc_netshelterpdu_power = CheckPlugin(
    name="apc_netshelterpdu_power",
    service_name="PDU %s",
    discovery_function=discover_apc_netshelterpdu_power,
    check_function=check_apc_netshelterpdu_power,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
