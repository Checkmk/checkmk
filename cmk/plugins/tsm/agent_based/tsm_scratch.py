#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResults,
    Service,
    StringTable,
)

Section = Mapping[str, int | None]


def parse_tsm_scratch(string_table: StringTable) -> Section:
    section = {}
    for line in string_table:
        if len(line) != 3:
            continue

        inst, tapes, library = line
        try:
            num_tapes = int(tapes)
        except ValueError:
            continue

        if inst != "default":
            item = f"{inst} / {library}"
        else:
            item = library

        section[item] = num_tapes
    return section


def discovery_tsm_scratch(section: Section) -> DiscoveryResult:
    yield from [Service(item=lib) for lib in section]


def check_tsm_scratch(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    num_tapes = section.get(item)

    if num_tapes is None:
        yield IgnoreResults()
        return

    levels_lower = params["levels_lower"]
    match levels_lower:
        case None:
            levels_lower = ("no_levels", None)

    yield from check_levels(
        num_tapes,
        metric_name="tapes_free",
        levels_lower=levels_lower,
        render_func=lambda x: "%d" % x,
        label="Found tapes",
    )


agent_section_tsm_scratch = AgentSection(
    name="tsm_scratch",
    parse_function=parse_tsm_scratch,
)


check_plugin_tsm_scratch = CheckPlugin(
    name="tsm_scratch",
    service_name="Scratch Pool %s",
    discovery_function=discovery_tsm_scratch,
    check_function=check_tsm_scratch,
    check_ruleset_name="scratch_tapes",
    check_default_parameters={"levels_lower": ("fixed", (7, 5))},
)
