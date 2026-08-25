#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except TypeError, ValueError:
        return 0


def discover_mikrotik_signal(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=network) for network, _strength, _mode in section)


def check_mikrotik_signal(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    warn, crit = params["levels_lower"]
    for network, strength_str, mode in section:
        if network == item:
            strength = saveint(strength_str)
            quality = 0
            if strength <= -50 or strength >= -100:
                quality = 2 * (strength + 100)
            quality = min(quality, 100)

            infotext = f"Signal quality {quality}% ({strength}dBm). Mode is: {mode}"
            if quality <= crit:
                state = State.CRIT
            elif quality <= warn:
                state = State.WARN
            else:
                state = State.OK
            yield Result(state=state, summary=infotext)
            yield Metric("quality", float(quality), levels=(warn, crit))
            return

    yield Result(state=State.UNKNOWN, summary="Network not found")


def parse_mikrotik_signal(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mikrotik_signal = SimpleSNMPSection(
    name="mikrotik_signal",
    parse_function=parse_mikrotik_signal,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14988.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14988.1.1.1.1.1",
        oids=["5.2", "4.2", "8.2"],
    ),
)

check_plugin_mikrotik_signal = CheckPlugin(
    name="mikrotik_signal",
    service_name="Signal %s",
    discovery_function=discover_mikrotik_signal,
    check_function=check_mikrotik_signal,
    check_ruleset_name="signal_quality",
    check_default_parameters={
        "levels_lower": (80.0, 70.0),
    },
)
