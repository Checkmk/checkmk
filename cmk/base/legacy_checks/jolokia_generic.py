#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


import time
from collections.abc import Callable, Iterable, Mapping
from typing import Literal

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, StringTable
from cmk.plugins.jolokia.agent_based.lib import jolokia_basic_split

check_info = {}

Section = Mapping[str, Mapping[str, float | str]]

DiscoveryResult = Iterable[tuple[str, dict]]


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
        yield from ((item, {}) for item, data in section.items() if data.get("type") == type_)

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


def check_jolokia_generic_string(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    value = data["value"]

    search_strings = params.get("match_strings", [])
    for search_string, status in search_strings:
        if search_string in value:
            yield status, f"{value}: {search_string} matches"
            return

    yield params.get("default_status", 0), value


check_info["jolokia_generic.string"] = LegacyCheckDefinition(
    name="jolokia_generic_string",
    service_name="JVM %s",
    sections=["jolokia_generic"],
    discovery_function=discover_type("string"),
    check_function=check_jolokia_generic_string,
    check_ruleset_name="generic_string",
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


def check_jolokia_generic_rate(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    rate = get_rate(get_value_store(), item, time.time(), data["value"], raise_overflow=True)
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield check_levels(rate, "generic_rate", levels)


check_info["jolokia_generic.rate"] = LegacyCheckDefinition(
    name="jolokia_generic_rate",
    service_name="JVM %s",
    sections=["jolokia_generic"],
    discovery_function=discover_type("rate"),
    check_function=check_jolokia_generic_rate,
    check_ruleset_name="generic_rate",
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


def check_jolokia_generic(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield check_levels(data["value"], "generic_number", levels)
    return


check_info["jolokia_generic"] = LegacyCheckDefinition(
    name="jolokia_generic",
    parse_function=parse_jolokia_generic,
    service_name="JVM %s",
    discovery_function=discover_type("number"),
    check_function=check_jolokia_generic,
    check_ruleset_name="generic_number",
)
