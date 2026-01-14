#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# [[[u'26', u'26']], [[u'45', u'15', u'45', u'15']]]


def discover_cmc_temp(info):
    # There are always two sensors
    yield "1", {}
    yield "2", {}


def check_cmc_temp(item, params, info):
    offset = int(item) - 1
    current_temp = int(info[0][0][offset])
    dev_high, dev_low = map(int, info[1][0][offset * 2 :][:2])
    return check_temperature(
        current_temp,
        params,
        "cmc_temp_%s" % item,
        dev_levels=(dev_high, dev_high),
        dev_levels_lower=(dev_low, dev_low),
    )


def parse_cmc_temp(string_table: Sequence[StringTable]) -> Sequence[StringTable] | None:
    return string_table if any(string_table) else None


check_info["cmc_temp"] = LegacyCheckDefinition(
    name="cmc_temp",
    parse_function=parse_cmc_temp,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2606.1"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2606.1.1",
            oids=["1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.1.4",
            oids=["4", "5", "6", "7"],
        ),
    ],
    service_name="Temperature Sensor %s",
    discovery_function=discover_cmc_temp,
    check_function=check_cmc_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
