#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from typing import Any

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.oracle.agent_based.liboracle import SectionPerformance


def parse_oracle_performance(string_table: StringTable) -> SectionPerformance:
    def _try_parse_int(s: str) -> int | None:
        try:
            return int(s)
        except ValueError:
            return None

    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    for line in string_table:
        if len(line) < 3:
            continue
        parsed.setdefault(line[0], {})
        parsed[line[0]].setdefault(line[1], {})
        counters = line[3:]
        if len(counters) == 1:
            parsed[line[0]][line[1]].setdefault(line[2], _try_parse_int(counters[0]))
        else:
            parsed[line[0]][line[1]].setdefault(line[2], list(map(_try_parse_int, counters)))

    return parsed


agent_section_oracle_performance = AgentSection(
    name="oracle_performance",
    parse_function=parse_oracle_performance,
)
