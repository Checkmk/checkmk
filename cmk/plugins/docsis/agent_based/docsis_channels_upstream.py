#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_rate,
    get_value_store,
    Metric,
    OIDEnd,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

# Old comments:
# Strange: Channel IDs seem to be not unique. But the second
# usage has '0' in the docsIfUpChannelFrequency...

# Info might look different: on the one hand the channel id is the connector
# on the other hand the OID. In some cases the channel id is not unique:

Section = dict[str, list[Any]]


def parse_docsis_channels_upstream(string_table: Sequence[StringTable]) -> Section:
    freq_info = string_table[0]
    freq_info_dict = {x[0]: x[1:] for x in freq_info}
    sig_info_dict = {x[0]: x[1:] for x in string_table[1]}
    cm_info_dict = {x[0]: x[1:] for x in string_table[2]}

    parsed: Section = {}
    for endoid, (cid, freq_str) in freq_info_dict.items():
        unique_name = (
            cid if len(freq_info) == len({x[1] for x in freq_info}) else (f"{endoid}.{cid}")
        )

        data: list[str] = []
        if endoid in sig_info_dict:
            data = sig_info_dict[endoid] + cm_info_dict.get(endoid, [])
        elif cid in sig_info_dict:
            data = sig_info_dict[cid] + cm_info_dict.get(cid, [])

        if data:
            parsed[unique_name] = [float(freq_str)] + data

    return parsed


def discover_docsis_channels_upstream(section: Section) -> DiscoveryResult:
    for unique_name, entry in section.items():
        if entry[0] != "0" and entry[4] != "0":
            yield Service(item=unique_name)


def check_docsis_channels_upstream(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item not in section:
        return

    entry = section[item]
    mhz, unerroreds, correcteds, uncorrectables, signal_noise = entry[:5]

    # Signal Noise
    sn_warn, sn_crit = params["signal_noise"]

    yield from check_levels(
        float(signal_noise) / 10,  # [dB]
        metric_name="signal_noise",
        levels_lower=("fixed", (sn_warn, sn_crit)),
        render_func=lambda x: f"{x:.1f} dB",
        label="Signal/Noise ratio",
    )

    fields: list[tuple[str, float, str, str, str]] = [
        ("frequency", float(mhz) / 1000000, "Frequency", "%.2f", " MHz"),
    ]
    if len(entry) >= 6:
        total, active, registered, avg_util = entry[5:9]
        fields += [
            ("total", int(total), "Modems total", "%d", ""),
            ("active", int(active), "Active", "%d", ""),
            ("registered", int(registered), "Registered", "%d", ""),
            ("util", int(avg_util), "Aaverage utilization", "%d", "%"),
        ]

    for varname, value, title, form, unit in fields:
        yield Result(state=State.OK, summary=title + ": " + (form + "%s") % (value, unit))
        yield Metric(varname, value)

    # Handle codewords. These are counters.
    now = time.time()
    rates: dict[str, float] = {}
    total_rate = 0.0
    for what, counter in [
        ("unerrored", int(unerroreds)),
        ("corrected", int(correcteds)),
        ("uncorrectable", int(uncorrectables)),
    ]:
        rate = get_rate(get_value_store(), what, now, counter, raise_overflow=True)
        rates[what] = rate
        total_rate += rate

    if total_rate:
        for what, title in [
            ("corrected", "corrected errors"),
            ("uncorrectable", "uncorrectable errors"),
        ]:
            ratio = rates[what] / total_rate
            perc = 100.0 * ratio
            warn, crit = params[what]
            infotext = f"{render.percent(perc)} {title}"

            state = State.OK
            if perc >= crit:
                state = State.CRIT
            elif perc >= warn:
                state = State.WARN

            if state is not State.OK:
                infotext += f" (warn/crit at {warn:.1f}/{crit:.1f}%)"

            yield Result(state=state, summary=infotext)
            yield Metric(f"codewords_{what}", ratio, levels=(warn / 100.0, crit / 100.0))


snmp_section_docsis_channels_upstream = SNMPSection(
    name="docsis_channels_upstream",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4115.820.1.0.0.0.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4115.900.2.0.0.0.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.827"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20858.2.600"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.10.127.1.1.2.1",
            oids=[OIDEnd(), "1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.10.127.1.1.4.1",
            oids=[OIDEnd(), "2", "3", "4", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.116.1.4.1.1",
            oids=[OIDEnd(), "3", "4", "5", "7"],
        ),
    ],
    parse_function=parse_docsis_channels_upstream,
)

check_plugin_docsis_channels_upstream = CheckPlugin(
    name="docsis_channels_upstream",
    service_name="Upstream Channel %s",
    discovery_function=discover_docsis_channels_upstream,
    check_function=check_docsis_channels_upstream,
    check_ruleset_name="docsis_channels_upstream",
    check_default_parameters={
        "signal_noise": (10.0, 5.0),  # dB
        "corrected": (5.0, 8.0),  # Percent
        "uncorrectable": (1.0, 2.0),  # Percent
    },
)
