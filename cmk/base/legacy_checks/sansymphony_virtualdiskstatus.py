#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<sansymphony_virtualdiskstatus>>>
# testvmfs01 Online
# vmfs10 Online


from collections.abc import Iterator, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}

Section = dict[str, str]


def parse_sansymphony_virtualdiskstatus(string_table: StringTable) -> Section:
    parsed: Section = {}
    for line in string_table:
        parsed.setdefault(line[0], " ".join(line[1:]))
    return parsed


def check_sansymphony_virtualdiskstatus(
    item: str, _no_params: Mapping[str, Any], parsed: Section
) -> Iterator[tuple[int, str]]:
    if not (data := parsed.get(item)):
        return
    state = 0 if data == "Online" else 2
    yield state, "Volume state is: %s" % data


def discover_sansymphony_virtualdiskstatus(
    section: Section,
) -> Iterator[tuple[str, dict[str, object]]]:
    yield from ((item, {}) for item in section)


check_info["sansymphony_virtualdiskstatus"] = LegacyCheckDefinition(
    name="sansymphony_virtualdiskstatus",
    parse_function=parse_sansymphony_virtualdiskstatus,
    service_name="sansymphony Virtual Disk %s",
    discovery_function=discover_sansymphony_virtualdiskstatus,
    check_function=check_sansymphony_virtualdiskstatus,
)
