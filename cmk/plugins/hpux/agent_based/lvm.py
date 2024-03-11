#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from dataclasses import dataclass

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


@dataclass(frozen=True, kw_only=True)
class Volume:
    group: str
    name: str
    states: Iterable[str]


Section = Mapping[str, Volume]


def parse_hpux_lvm(string_table: StringTable) -> Section:
    section = {}
    vg_name = ""
    for line in string_table:
        if line[0].startswith("vg_name"):
            vg_name = line[0].split("=")[1]
        elif line[0].startswith("lv_name"):
            lv_name = line[0].split("=")[1]
            section[lv_name] = Volume(
                group=vg_name,
                name=lv_name,
                states=line[1].split("=")[1].split(","),
            )
    return section


agent_section_hpux_lvm = AgentSection(
    name="hpux_lvm",
    parse_function=parse_hpux_lvm,
)


_OK_STATES = {"available", "syncd", "snapshot", "space_efficient"}


def _compute_state(observed_states: Iterable[str]) -> State:
    _non_ok_states = set(observed_states) - _OK_STATES
    return State.CRIT if _non_ok_states else State.OK


def discover_hpux_lvm(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_hpux_lvm(item: str, section: Section) -> CheckResult:
    if (volume := section.get(item)) is None:
        return

    yield Result(state=_compute_state(volume.states), summary=f"Status: {','.join(volume.states)}")
    yield Result(state=State.OK, summary=f"Volume group: {volume.group}")


check_plugin_hpux_lvm = CheckPlugin(
    name="hpux_lvm",
    service_name="Logical Volume %s",
    discovery_function=discover_hpux_lvm,
    check_function=check_hpux_lvm,
)
