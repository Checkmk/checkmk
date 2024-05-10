#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def parse_zebra_model(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


def inventory_zebra_model(section: Sequence[StringTable]) -> DiscoveryResult:
    if any(section):
        yield Service()


def check_zebra_model(section: Sequence[StringTable]) -> CheckResult:
    model, serial, release = None, None, None

    if section[0]:
        model, serial, release, serial_maybe = section[0][0]
        if not serial:
            serial = serial_maybe

    if not model:
        model = section[2][0][0]

    if not release:
        release = section[1][0][0]

    yield Result(state=State.OK, summary="Zebra model: %s" % model)

    if serial:
        yield Result(state=State.OK, summary="Serial number: %s" % serial)

    if release:
        yield Result(state=State.OK, summary="Firmware release: %s" % release)


snmp_section_zebra_model = SNMPSection(
    name="zebra_model",
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
    parse_function=parse_zebra_model,
)
check_plugin_zebra_model = CheckPlugin(
    name="zebra_model",
    service_name="Zebra Printer Model",
    discovery_function=inventory_zebra_model,
    check_function=check_zebra_model,
)
