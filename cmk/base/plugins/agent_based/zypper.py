#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections import Counter
from typing import Any, Mapping, NamedTuple

from .agent_based_api.v1 import register, Result, Service, State, type_defs
from .agent_based_api.v1.type_defs import CheckResult


class ZypperUpdates(NamedTuple):
    patch_types: list[str]
    locks: list[str] = []


class Error(str):
    pass


Section = ZypperUpdates | Error


def parse_zypper(string_table: type_defs.StringTable) -> Section:
    patch_types = []
    locks = []

    firstline = " ".join(string_table[0]) if string_table else ""
    if re.match("ERROR:", firstline):
        return Error(firstline)

    for line in string_table:
        match line:
            case [_, _, _, pt, n] | [_, _, _, pt, n, _] | [_, _, pt, _, _, n, *_]:
                if (patch_type := pt.strip()) and n.lower().strip() == "needed":
                    patch_types.append(patch_type)
            case [_, lock, _, _]:
                locks.append(lock)

    return ZypperUpdates(patch_types=patch_types, locks=locks)


def discover_zypper(section: Section) -> type_defs.DiscoveryResult:
    yield Service()


def check_zypper(params: Mapping[str, Any], section: Section) -> CheckResult:
    if isinstance(section, Error):
        yield Result(state=State.UNKNOWN, summary=section)
        return

    yield Result(state=State.OK, summary=f"{len(section.patch_types)} updates")
    if section.locks:
        lock_count = len(section.locks)
        yield Result(state=State.WARN, summary=f"{lock_count} locks")

    state_map = {
        "security": State.CRIT,
        "recommended": State.WARN,
    }
    for type_, count in sorted(Counter(section.patch_types).items(), key=lambda item: item[0]):
        yield Result(state=state_map.get(type_, State.OK), notice=f"{type_}: {count}")


register.agent_section(
    name="zypper",
    parse_function=parse_zypper,
)

register.check_plugin(
    name="zypper",
    service_name="Zypper Updates",
    discovery_function=discover_zypper,
    check_function=check_zypper,
    check_ruleset_name="zypper",
    check_default_parameters={},
)
