#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterable, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_value_store, OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.casa import DETECT_CASA
from cmk.plugins.lib.cpu_util import check_cpu_util

check_info = {}


def parse_casa_info_util(info):
    entity_names = {int(k): v for k, v in (x for x in info[0])}
    data = {}
    for entry in info[1]:
        entry_nr = int(entry[0])
        name = entity_names[entry_nr]  # e.g. "Module 1 QEM".
        # Drop "QEM" in order to be consistent with other DTCS checks...
        if name.startswith("Module "):
            name = name.rsplit(None, 1)[0]
        data[name] = {
            "cpu_util": entry[1],
        }
    return data


def inventory_casa_cpu_util(string_table: StringTable) -> Iterable[tuple[str, dict]]:
    for key, value in parse_casa_info_util(string_table).items():
        if value.get("cpu_util"):
            yield key, {}


def check_casa_cpu_util(item, params, info):
    data = parse_casa_info_util(info)
    if (values := data.get(item)) is None:
        return

    value = float(values["cpu_util"])

    yield from check_cpu_util(
        util=value,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_casa_cpu_util(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["casa_cpu_util"] = LegacyCheckDefinition(
    name="casa_cpu_util",
    parse_function=parse_casa_cpu_util,
    detect=DETECT_CASA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.13.1.1.1",
            oids=[OIDEnd(), "4"],
        ),
    ],
    service_name="CPU utilization %s",
    discovery_function=inventory_casa_cpu_util,
    check_function=check_casa_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
)
