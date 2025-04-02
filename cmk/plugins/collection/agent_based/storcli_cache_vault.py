#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.broadcom_storage.lib import megaraid

_KNOWN_PROPERTIES: Final = (
    "State",
    "Replacement required",
    "Capacitance",
)


class CacheVault(NamedTuple):
    state: str
    needs_replacement: bool
    capacitance_perc: float


Section = Mapping[str, CacheVault]


_RawCacheVaultProperties = dict[str, str]
_RawSection = dict[str, _RawCacheVaultProperties]


def _extract_controller(line: str) -> str | None:
    return f"/c{line.split('=')[1].strip()}" if line.startswith("Controller =") else None


def parse_storcli_cache_vault(string_table: StringTable) -> Section:
    raw_section: _RawSection = {}
    raw_roperties: _RawCacheVaultProperties = {}

    for (line,) in (l for l in string_table if l):
        if (item := _extract_controller(line)) is not None:
            raw_roperties = raw_section.setdefault(item, {})
            continue

        for prop in _KNOWN_PROPERTIES:
            if line.startswith(prop):
                raw_roperties[prop] = line[len(prop) :].strip()

    return {
        k: CacheVault(
            state=megaraid.expand_abbreviation(v["State"]),
            needs_replacement=v["Replacement required"].lower() != "no",
            capacitance_perc=float(v["Capacitance"].split("%")[0]),
        )
        for k, v in raw_section.items()
        if "State" in v
    }


agent_section_storcli_cache_vault = AgentSection(
    name="storcli_cache_vault",
    parse_function=parse_storcli_cache_vault,
)


def discover_storcli_cache_vault(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_storcli_cache_vault(item: str, section: Section) -> CheckResult:
    if (vault := section.get(item)) is None:
        return

    yield Result(
        state=State.OK if vault.state == "Optimal" else State.CRIT,
        summary=vault.state.capitalize(),
    )

    yield from check_levels_v1(
        vault.capacitance_perc, render_func=render.percent, label="Capacitance"
    )

    if vault.needs_replacement:
        yield Result(state=State.WARN, summary="Replacement required")


check_plugin_storcli_cache_vault = CheckPlugin(
    name="storcli_cache_vault",
    service_name="RAID cache vault %s",
    discovery_function=discover_storcli_cache_vault,
    check_function=check_storcli_cache_vault,
)
