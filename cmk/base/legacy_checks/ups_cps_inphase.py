#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.ups.lib import DETECT_UPS_CPS

check_info = {}


def parse_ups_cps_inphase(
    string_table: StringTable,
) -> Mapping[str, Mapping[str, float]] | None:
    if not string_table:
        return None

    parsed = {}
    for index, stat_name in enumerate(("voltage", "frequency")):
        try:
            parsed[stat_name] = float(string_table[0][index]) / 10
        except ValueError:
            continue

    return {"1": parsed} if parsed else {}


def discover_ups_cps_inphase(parsed):
    if parsed:
        yield "1", {}


check_info["ups_cps_inphase"] = LegacyCheckDefinition(
    name="ups_cps_inphase",
    detect=DETECT_UPS_CPS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.3.2",
        oids=["1", "4"],
    ),
    parse_function=parse_ups_cps_inphase,
    service_name="UPS Input Phase %s",
    discovery_function=discover_ups_cps_inphase,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
