#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.318.1.1.12.1.1.0  "sf9pdu1" --> PowerNet-MIB::rPDUIdentName.0
# .1.3.6.1.4.1.318.1.1.12.1.9.0 1 --> PowerNet-MIB::rPDUIdentDeviceNumPhases.0
# .1.3.6.1.4.1.318.1.1.12.1.16.0 0 --> PowerNet-MIB::rPDUIdentDevicePowerWatts.0
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.1 160 --> PowerNet-MIB::rPDULoadStatusLoad.1 (measured in tenths of Amps)
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.1 1 --> PowerNet-MIB::rPDULoadStatusLoadState.1

# .1.3.6.1.4.1.318.1.1.12.1.1.0 FOOBAR --> PowerNet-MIB::rPDUIdentName.0
# .1.3.6.1.4.1.318.1.1.12.1.9.0 1 --> PowerNet-MIB::rPDUIdentDeviceNumPhases.0
# .1.3.6.1.4.1.318.1.1.12.1.16.0 1587 --> PowerNet-MIB::rPDUIdentDevicePowerWatts.0
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.1 0 --> PowerNet-MIB::rPDULoadStatusLoad.1
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.2 0 --> PowerNet-MIB::rPDULoadStatusLoad.2
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.2.3 0 --> PowerNet-MIB::rPDULoadStatusLoad.3
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.1 1 --> PowerNet-MIB::rPDULoadStatusLoadStates.1
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.2 1 --> PowerNet-MIB::rPDULoadStatusLoadStates.2
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.3.3 1 --> PowerNet-MIB::rPDULoadStatusLoadStates.3
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.4.1 1 --> PowerNet-MIB::rPDULoadStatusPhaseNumber.1
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.4.2 0 --> PowerNet-MIB::rPDULoadStatusPhaseNumber.2
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.4.3 0 --> PowerNet-MIB::rPDULoadStatusPhaseNumber.3
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.5.1 0 --> PowerNet-MIB::rPDULoadStatusBankNumber.1
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.5.2 1 --> PowerNet-MIB::rPDULoadStatusBankNumber.2
# .1.3.6.1.4.1.318.1.1.12.2.3.1.1.5.3 2 --> PowerNet-MIB::rPDULoadStatusBankNumber.3

# examples num phase/banks: 1/0,    => parsed = device phase
#                           1/2,    => parsed = device phase + 2 banks
#                           3/0     => parsed = device phase + 3 phases


from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, TypedDict

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

type StatusInfo = tuple[float, tuple[int, str]]


class Power(TypedDict):
    power: NotRequired[float]
    current: NotRequired[StatusInfo]


type Section = Mapping[str, Power]


STATE_MAP = {
    "1": (0, "load normal"),
    "2": (2, "load low"),
    "3": (1, "load near over load"),
    "4": (2, "load over load"),
}


def get_status_info(amperage_str: str, device_state: str) -> StatusInfo:
    return float(amperage_str) / 10, STATE_MAP[device_state]


def parse_apc_rackpdu_power(string_table: Sequence[StringTable]) -> Section | None:
    if not any(string_table):
        return None

    parsed = dict[str, Power]()
    device_info, n_phases, phase_bank_info = string_table
    pdu_ident_name, power_str = device_info[0]
    device_name = "Device %s" % pdu_ident_name

    parsed.setdefault(device_name, Power(power=float(power_str)))

    if n_phases[0][0] == "1":
        parsed[device_name]["current"] = get_status_info(*phase_bank_info[0][:2])
        phase_bank_info = phase_bank_info[1:]

    for amperage_str, device_state, phase_num, bank_num in phase_bank_info:
        if bank_num != "0":
            name_part = "Bank"
            num = bank_num
        elif phase_num != "0":
            name_part = "Phase"
            num = phase_num
        else:
            continue

        parsed.setdefault(
            f"{name_part} {num}", Power(current=get_status_info(amperage_str, device_state))
        )
    return parsed


snmp_section_apc_rackpdu_power = SNMPSection(
    name="apc_rackpdu_power",
    parse_function=parse_apc_rackpdu_power,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.1",
            oids=[
                "1",  # rPDUIdentName
                "16",  # rPDUIdentDevicePowerWatts
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.2.1",
            oids=[
                "2",  # rPDULoadDevNumPhases
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.2.3.1.1",
            oids=[
                "2",  # rPDULoadStatusLoad
                "3",  # rPDULoadStatusLoadState
                "4",  # rPDULoadStatusPhaseNumber
                "5",  # rPDULoadStatusBankNumber
            ],
        ),
    ],
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "apc web/snmp"),
        exists(".1.3.6.1.4.1.318.1.1.12.1.*"),
    ),
)


def discover_apc_rackpdu_power(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_apc_rackpdu_power(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (power := section.get(item)) is None:
        return

    if (entry := power.get("current")) is not None:
        value, (state_code, state_text) = entry
        yield from check_levels(
            value,
            "current",
            params=params.get("current"),
            human_readable_func=lambda v: f"{v:.1f} A",
            infoname="Current",
        )
        yield Result(state=State(state_code), summary=state_text)

    if (value_power := power.get("power")) is not None:
        yield from check_levels(
            value_power,
            "power",
            params.get("power"),
            human_readable_func=lambda v: f"{v:.1f} W",
            infoname="Power",
        )


check_plugin_apc_rackpdu_power = CheckPlugin(
    name="apc_rackpdu_power",
    service_name="PDU %s",
    discovery_function=discover_apc_rackpdu_power,
    check_function=check_apc_rackpdu_power,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
