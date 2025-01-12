#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Format of a response string according to the manufacturer documentation:
# status@item_count@item[1].name@item[1].value@...item[n].name@item[n].value@$
# Beware, though: Item names are not always unique!

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import StringTable


def parse_ddn_s2a_api_response(string_table: StringTable) -> Mapping[str, Sequence[str]]:
    response_string = " ".join(string_table[0])
    raw_fields = response_string.split("@")

    parsed: dict[str, list[str]] = {}
    for field_name, field_value in zip(raw_fields[2:-2:2], raw_fields[3:-1:2]):
        parsed.setdefault(field_name, []).append(field_value)
    return parsed
