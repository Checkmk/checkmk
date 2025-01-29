#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from typing import Any

from cmk.base.check_legacy_includes.apc_ats import (
    CommunictionStatus,
    OverCurrentStatus,
    PowerSupplyStatus,
    RedunandancyStatus,
    Source,
    Status,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT_ATS

check_info = {}


def parse_apc_ats_status(info: StringTable) -> Status | None:
    if len(info) == 1:
        return Status.from_raw(info[0])
    return None


def inventory_apc_ats_status(parsed: Status) -> Iterable[tuple[None, dict]]:
    if parsed and parsed.selected_source:
        yield None, {"power_source": parsed.selected_source.value}


def check_apc_ats_status(_no_item: Any, params: dict, parsed: Status) -> Iterable:
    source = params["power_source"]
    state = 0
    messages = []

    # current source of power
    source_parsed = Source(source)
    if source_parsed != parsed.selected_source:
        state = 2
        assert parsed.selected_source is not None
        messages.append(
            "Power source Changed from %s to %s(!!)"
            % (source_parsed.name, parsed.selected_source.name)
        )
    else:
        messages.append("Power source %s selected" % source_parsed.name)

    # current communication status of the Automatic Transfer Switch.
    if parsed.com_status == CommunictionStatus.NeverDiscovered:
        state = max(1, state)
        messages.append("Communication Status: never Discovered(!)")
    elif parsed.com_status == CommunictionStatus.Lost:
        state = 2
        messages.append("Communication Status: lost(!!)")

    # current redundancy state of the ATS.
    # Lost(1) indicates that the ATS is unable to switch over to the alternate power source
    # if the current source fails. Redundant(2) indicates that the ATS will switch
    # over to the alternate power source if the current source fails.
    if parsed.redundancy == RedunandancyStatus.Lost:
        state = 2
        messages.append("redundancy lost(!!)")
    else:
        messages.append("Device fully redundant")

    # current state of the ATS. atsOverCurrent(1) indicates that the ATS has i
    # exceeded the output current threshold and will not allow a switch
    # over to the alternate power source if the current source fails.
    # atsCurrentOK(2) indicates that the output current is below the output current threshold.
    if parsed.overcurrent == OverCurrentStatus.Exceeded:
        state = 2
        messages.append("exceeded ouput current threshold(!!)")

    for powersource in parsed.powersources:
        if powersource is None:
            continue
        if powersource.status != PowerSupplyStatus.OK:
            state = 2
            messages.append(f"{powersource.name} power supply failed(!!)")

    return state, ", ".join(messages)


check_info["apc_ats_status"] = LegacyCheckDefinition(
    name="apc_ats_status",
    parse_function=parse_apc_ats_status,
    detect=DETECT_ATS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.8.5.1",
        oids=["1.0", "2.0", "3.0", "4.0", "5.0", "6.0", "17.0", "18.0"],
    ),
    service_name="ATS Status",
    discovery_function=inventory_apc_ats_status,
    check_function=check_apc_ats_status,
    check_default_parameters={},
)
