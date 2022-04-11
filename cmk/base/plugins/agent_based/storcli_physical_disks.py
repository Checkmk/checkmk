#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import megaraid


def parse_storcli_physical_disks(string_table: StringTable) -> megaraid.SectionPDisks:
    raw_section: dict[str, dict[str, str]] = {}
    raw_disk: dict[str, str] = {}
    iter_lines = iter(string_table)

    for words in iter_lines:
        if words[0] == "Drive" and words[-1] == ":":
            raw_disk = raw_section.setdefault(words[1], {"name": words[1]})
            continue

        if words[0] == "EID:Slt" and words[2] == "State":
            _ = next(iter_lines)
            _, _, state, *_rest = next(iter_lines)
            raw_disk["state"] = state
            continue

        if words[:3] == ["Predictive", "Failure", "Count"]:
            raw_disk["failure_count"] = words[4]

    return {
        name: megaraid.PDisk(
            name=raw_disk["name"],
            state=megaraid.expand_abbreviation(raw_disk["state"]),
            failures=None if (c := raw_disk.get("failure_count")) is None else int(c),
        )
        for name, raw_disk in raw_section.items()
    }


register.agent_section(
    name="storcli_physical_disks",
    parsed_section_name="megaraid_pdisks",
    parse_function=parse_storcli_physical_disks,
)
