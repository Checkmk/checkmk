#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import megaraid


def parse_storcli_virtual_disks(string_table: StringTable) -> megaraid.SectionLDisks:
    raw = {}
    lines = iter(string_table)
    for first_word, *rest in lines:
        if rest != [":"] or not (first_word.startswith("/c") and "/v" in first_word):
            continue

        item = first_word
        _, _, header, _, row = next(lines), next(lines), next(lines), next(lines), next(lines)
        header.insert(header.index("Size") + 1, "Unit")
        raw[item] = dict(zip(header, row))

    return {
        k: megaraid.LDisk(
            state=megaraid.expand_abbreviation(v["State"]),
        )
        for k, v in raw.items()
    }


register.agent_section(
    name="storcli_virtual_disks",
    parsed_section_name="megaraid_ldisks",
    parse_function=parse_storcli_virtual_disks,
)
