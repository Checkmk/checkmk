#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)

Section = Mapping[str, Mapping[str, str]]


def parse_informix_locks(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, str]] = {}
    instance: str | None = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and line[0] == "LOCKS":
            parsed.setdefault(instance, {"locks": line[1], "type": line[2]})

    return parsed


def discover_informix_locks(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_informix_locks(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return
    data = section[item]
    locks = int(data["locks"])
    warn, crit = params["levels"]

    yield from check_levels_v1(
        locks,
        metric_name="locks",
        levels_upper=(warn, crit),
        label=f"Type: {data['type']}, Locks",
    )


agent_section_informix_locks = AgentSection(
    name="informix_locks",
    parse_function=parse_informix_locks,
)


check_plugin_informix_locks = CheckPlugin(
    name="informix_locks",
    service_name="Informix Locks %s",
    discovery_function=discover_informix_locks,
    check_function=check_informix_locks,
    check_ruleset_name="informix_locks",
    check_default_parameters={
        "levels": (70, 80),
    },
)
