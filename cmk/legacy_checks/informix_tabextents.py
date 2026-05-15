#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Sequence[Mapping[str, str]]]


def parse_informix_tabextents(string_table: StringTable) -> Section:
    parsed: dict[str, list[dict[str, str]]] = {}
    instance: str | None = None
    entry: dict[str, str] | None = None
    for line in string_table:
        if instance is not None and line == ["(constant)", "TABEXTENTS"]:
            entry = {}
            parsed.setdefault(instance, [])
            parsed[instance].append(entry)

        elif line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif entry is not None:
            entry.setdefault(line[0], line[1])

    return parsed


def discover_informix_tabextents(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_informix_tabextents(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item not in section:
        return

    max_extents = -1
    long_output = []
    for entry in section[item]:
        max_extents = max(max_extents, int(entry["extents"]))
        long_output.append(
            f"[{entry['db']}/{entry['tab']}] Extents: {entry['extents']}, Rows: {entry['nrows']}"
        )

    yield from check_levels_v1(
        max_extents,
        metric_name="max_extents",
        levels_upper=params["levels"],
        label="Maximal extents",
        render_func=str,
    )
    yield Result(state=State.OK, notice="\n".join(long_output))


agent_section_informix_tabextents = AgentSection(
    name="informix_tabextents",
    parse_function=parse_informix_tabextents,
)


check_plugin_informix_tabextents = CheckPlugin(
    name="informix_tabextents",
    service_name="Informix Table Extents %s",
    discovery_function=discover_informix_tabextents,
    check_function=check_informix_tabextents,
    check_ruleset_name="informix_tabextents",
    check_default_parameters={
        "levels": (40, 70),
    },
)
