#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Callable, Mapping
from typing import Any, Literal

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.jolokia.agent_based.lib import jolokia_basic_split

Section = Mapping[str, Mapping[str, float | str]]


def parse_jolokia_generic(string_table: StringTable) -> Section:
    value: str | float
    parsed = {}
    for line in string_table:
        try:
            instance, mbean, value, type_ = jolokia_basic_split(line, 4)
            if type_ in ("rate", "number"):
                value = float(value)
        except ValueError:
            continue
        item = f"{instance} MBean {mbean}"
        parsed[item] = {"value": value, "type": type_}

    return parsed


def discover_type(
    type_: Literal["string", "rate", "number"],
) -> Callable[[Section], DiscoveryResult]:
    def _discover_bound_type(section: Section) -> DiscoveryResult:
        yield from (
            Service(item=item) for item, data in section.items() if data.get("type") == type_
        )

    return _discover_bound_type


# .
#   .--String--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ _ __(_)_ __   __ _                      |
#   |                   \___ \| __| '__| | '_ \ / _` |                     |
#   |                    ___) | |_| |  | | | | | (_| |                     |
#   |                   |____/ \__|_|  |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def check_jolokia_generic_string(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    value = str(data["value"])

    search_strings = params.get("match_strings", [])
    for search_string, status in search_strings:
        if search_string in value:
            yield Result(state=State(status), summary=f"{value}: {search_string} matches")
            return

    yield Result(state=State(params.get("default_status", 0)), summary=value)


check_plugin_jolokia_generic_string = CheckPlugin(
    name="jolokia_generic_string",
    service_name="JVM %s",
    sections=["jolokia_generic"],
    discovery_function=discover_type("string"),
    check_function=check_jolokia_generic_string,
    check_ruleset_name="generic_string",
    check_default_parameters={},
)

# .
#   .--Rate----------------------------------------------------------------.
#   |                         ____       _                                 |
#   |                        |  _ \ __ _| |_ ___                           |
#   |                        | |_) / _` | __/ _ \                          |
#   |                        |  _ < (_| | ||  __/                          |
#   |                        |_| \_\__,_|\__\___|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_jolokia_generic_rate(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    rate = get_rate(get_value_store(), item, time.time(), float(data["value"]), raise_overflow=True)
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield from check_levels(rate, "generic_rate", levels)


check_plugin_jolokia_generic_rate = CheckPlugin(
    name="jolokia_generic_rate",
    service_name="JVM %s",
    sections=["jolokia_generic"],
    discovery_function=discover_type("rate"),
    check_function=check_jolokia_generic_rate,
    check_ruleset_name="generic_rate",
    check_default_parameters={},
)

# .
#   .--Number--------------------------------------------------------------.
#   |                _   _                 _                               |
#   |               | \ | |_   _ _ __ ___ | |__   ___ _ __                 |
#   |               |  \| | | | | '_ ` _ \| '_ \ / _ \ '__|                |
#   |               | |\  | |_| | | | | | | |_) |  __/ |                   |
#   |               |_| \_|\__,_|_| |_| |_|_.__/ \___|_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_jolokia_generic(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield from check_levels(float(data["value"]), "generic_number", levels)


agent_section_jolokia_generic = AgentSection(
    name="jolokia_generic",
    parse_function=parse_jolokia_generic,
)


check_plugin_jolokia_generic = CheckPlugin(
    name="jolokia_generic",
    service_name="JVM %s",
    discovery_function=discover_type("number"),
    check_function=check_jolokia_generic,
    check_ruleset_name="generic_number",
    check_default_parameters={},
)
