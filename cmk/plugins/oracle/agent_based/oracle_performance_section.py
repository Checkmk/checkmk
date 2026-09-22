#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.oracle.agent_based.liboracle import (
    classify_line,
    Error,
    InstancePerformance,
    Ok,
    Parsed,
    SectionPerformance,
)


def parse_oracle_performance(string_table: StringTable) -> SectionPerformance:
    def _try_parse_int(s: str) -> int | None:
        try:
            return int(s)
        except ValueError:
            return None

    counters_by_sid: dict[str, dict[str, dict[str, Any]]] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match classify_line(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                if len(line) < 3 or not line[0]:
                    continue
                group = counters_by_sid.setdefault(line[0], {}).setdefault(line[1], {})
                counters = line[3:]
                if len(counters) == 1:
                    group.setdefault(line[2], _try_parse_int(counters[0]))
                else:
                    group.setdefault(line[2], list(map(_try_parse_int, counters)))

    parsed: dict[str, Parsed[InstancePerformance]] = {
        sid: Ok(counters) for sid, counters in counters_by_sid.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


agent_section_oracle_performance = AgentSection(
    name="oracle_performance",
    parse_function=parse_oracle_performance,
)
