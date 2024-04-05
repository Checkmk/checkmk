#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree

from cmk.agent_based.v2.type_defs import StringTable


def inventory_zebra_model(info):
    if info[0] != [] or info[1] != [] or info[2] != []:
        return [(None, {})]
    return []


def check_zebra_model(_no_item, _no_params, info):
    model, serial, release = None, None, None

    if info[0]:
        model, serial, release, serial_maybe = info[0][0]
        if not serial:
            serial = serial_maybe

    if not model:
        model = info[2][0][0]

    if not release:
        release = info[1][0][0]

    yield 0, "Zebra model: %s" % model

    if serial:
        yield 0, "Serial number: %s" % serial

    if release:
        yield 0, "Firmware release: %s" % release


def parse_zebra_model(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["zebra_model"] = LegacyCheckDefinition(
    parse_function=parse_zebra_model,
    detect=contains(".1.3.6.1.2.1.1.1.0", "zebra"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.10642",
            oids=["1.1.0", "200.19.5.0", "1.2.0", "1.9.0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.683.1.9",
            oids=["0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.683.6.2.3.2.1.15",
            oids=["1"],
        ),
    ],
    service_name="Zebra Printer Model",
    discovery_function=inventory_zebra_model,
    check_function=check_zebra_model,
)
