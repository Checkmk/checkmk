#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.ups_socomec.lib import DETECT_SOCOMEC

check_info = {}

Section = dict[str, dict[str, tuple[int, None]]]


def parse_ups_socomec_outphase(string_table: StringTable) -> Section:
    parsed: Section = {}
    for index, rawvolt, rawcurr, rawload in string_table:
        parsed["Phase " + index] = {
            "voltage": (int(rawvolt) // 10, None),  # The actual precision does not appear to
            "current": (int(rawcurr) // 10, None),  # go beyond degrees, thus we drop the trailing 0
            "output_load": (int(rawload), None),
        }
    return parsed


def check_ups_socomec_outphase(
    item: str, params: Mapping[str, Any], parsed: Section
) -> Iterator[tuple[int, str] | tuple[int, str, list[Any]]]:
    if not item.startswith("Phase"):
        # fix item names discovered before 1.2.7
        item = "Phase %s" % item
    yield from check_elphase(item, params, parsed)


def discover_ups_socomec_outphase(section: Section) -> Iterator[tuple[str, dict[str, object]]]:
    yield from ((item, {}) for item in section)


check_info["ups_socomec_outphase"] = LegacyCheckDefinition(
    name="ups_socomec_outphase",
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.4.4.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_ups_socomec_outphase,
    service_name="Output %s",
    discovery_function=discover_ups_socomec_outphase,
    check_function=check_ups_socomec_outphase,
    check_ruleset_name="ups_outphase",
    # Phase Index, Voltage/dV, Current/dA, Load/%,
    check_default_parameters={
        "voltage": (210, 200),
        "output_load": (80, 90),
    },
)
