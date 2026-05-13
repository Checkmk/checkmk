#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.2.1.1.1.0 Linux gateway1 2.6.18-92cp #1 SMP Tue Dec 4 21:44:22 IST 2012 i686
# .1.3.6.1.4.1.2620.1.1.4.0 131645
# .1.3.6.1.4.1.2620.1.1.5.0 0
# .1.3.6.1.4.1.2620.1.1.6.0 1495
# .1.3.6.1.4.1.2620.1.1.7.0 16297

import time
from collections.abc import Mapping, Sequence

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.checkpoint.lib import DETECT

Section = Mapping[str, int]


def parse_checkpoint_packets(string_table: Sequence[StringTable]) -> Section:
    parsed: dict[str, int] = {}
    for key, main_index, sub_index in [
        ("Accepted", 0, 0),
        ("Rejected", 0, 1),
        ("Dropped", 0, 2),
        ("Logged", 0, 3),
        ("EspEncrypted", 1, 0),
        ("EspDecrypted", 1, 1),
    ]:
        try:
            parsed[key] = int(string_table[main_index][0][sub_index])
        except (IndexError, ValueError):
            pass
    return parsed


def discover_checkpoint_packets(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_checkpoint_packets(
    params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    this_time = time.time()
    for name, value in section.items():
        key = name.lower()
        yield from check_levels(
            get_rate(get_value_store(), key, this_time, value, raise_overflow=True),
            levels_upper=params.get(key),
            metric_name=key,
            render_func=lambda x: f"{x:.1f} pkts/s",
            label=name,
        )


snmp_section_checkpoint_packets = SNMPSection(
    name="checkpoint_packets",
    detect=DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2620.1.1",
            oids=["4", "5", "6", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2620.1.2.5.4",
            oids=["5", "6"],
        ),
    ],
    parse_function=parse_checkpoint_packets,
)


check_plugin_checkpoint_packets = CheckPlugin(
    name="checkpoint_packets",
    service_name="Packet Statistics",
    discovery_function=discover_checkpoint_packets,
    check_function=check_checkpoint_packets,
    check_ruleset_name="checkpoint_packets",
    check_default_parameters={
        "accepted": (100000, 200000),
        "rejected": (100000, 200000),
        "dropped": (100000, 200000),
        "logged": (100000, 200000),
        "espencrypted": (100000, 200000),
        "espdecrypted": (100000, 200000),
    },
)
