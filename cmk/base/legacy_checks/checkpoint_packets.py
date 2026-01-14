#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, SNMPTree
from cmk.plugins.checkpoint.lib import DETECT

check_info = {}

# .1.3.6.1.2.1.1.1.0 Linux gateway1 2.6.18-92cp #1 SMP Tue Dec 4 21:44:22 IST 2012 i686
# .1.3.6.1.4.1.2620.1.1.4.0 131645
# .1.3.6.1.4.1.2620.1.1.5.0 0
# .1.3.6.1.4.1.2620.1.1.6.0 1495
# .1.3.6.1.4.1.2620.1.1.7.0 16297


def parse_checkpoint_packets(string_table):
    parsed = {}
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


def discover_checkpoint_packets(parsed):
    if parsed:
        return [(None, {})]
    return []


def check_checkpoint_packets(_no_item, params, parsed):
    this_time = time.time()
    for name, value in parsed.items():
        key = name.lower()
        yield check_levels(
            get_rate(get_value_store(), key, this_time, value, raise_overflow=True),
            key,
            params.get(key),
            human_readable_func=lambda x: f"{x:.1f} pkts/s",
            infoname=name,
        )


check_info["checkpoint_packets"] = LegacyCheckDefinition(
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
