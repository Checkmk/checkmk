#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.ups.lib import DETECT_UPS_GENERIC

Section = Mapping[str, float | None]


def parse_ups_in_freq(string_table: StringTable) -> Section:
    parsed: dict[str, float | None] = {}
    for name, freq_str in string_table:
        try:
            freq: float | None = int(freq_str) / 10.0
        except ValueError:
            freq = None
        parsed.setdefault(name, freq)
    return parsed


def discover_ups_in_freq(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item) for item, freq in section.items() if freq is not None and freq > 0
    )


def check_ups_in_freq(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    freq = section.get(item)
    if freq is None:
        return

    warn, crit = params["levels_lower"]
    state = State.OK
    if freq < crit:
        state = State.CRIT
    elif freq < warn:
        state = State.WARN

    infotext = "%.1f Hz" % freq
    if state is not State.OK:
        infotext += f" (warn/crit below {warn} Hz/{crit} Hz)"

    yield Result(state=state, summary=infotext)
    yield Metric("in_freq", freq, levels=(warn, crit), boundaries=(30, 70))


snmp_section_ups_in_freq = SimpleSNMPSection(
    name="ups_in_freq",
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.3.3.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_ups_in_freq,
)


check_plugin_ups_in_freq = CheckPlugin(
    name="ups_in_freq",
    service_name="IN frequency phase %s",
    discovery_function=discover_ups_in_freq,
    check_function=check_ups_in_freq,
    check_ruleset_name="efreq",
    check_default_parameters={"levels_lower": (45, 40)},
)
