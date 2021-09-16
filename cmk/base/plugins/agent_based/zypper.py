#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Any, Dict, List, Mapping, NamedTuple

from .agent_based_api.v1 import register, Result, Service, State, type_defs
from .agent_based_api.v1.type_defs import CheckResult


class ZypperUpdates(NamedTuple):
    patch_types: Dict[str, int] = {}
    updates: int = 0
    locks: List[str] = []
    error: str = ""


Section = ZypperUpdates


def parse_zypper(string_table: type_defs.StringTable) -> Section:
    patch_types: Dict[str, int] = {}
    updates: int = 0
    locks: List[str] = []

    firstline = " ".join(string_table[0]) if string_table else ""
    if re.match("ERROR:", firstline):
        return Section(error=firstline)

    for line in string_table:
        # 5 patches needed (2 security patches)
        if len(line) >= 5:
            patch_type = None
            if len(line) >= 7 and line[5].lower().strip() == "needed":  # since SLES12
                patch_type = line[2].strip()
            elif line[4].lower().strip() == "needed":
                patch_type = line[3].strip()
            if patch_type:
                patch_types.setdefault(patch_type, 0)
                patch_types[patch_type] += 1
                updates += 1
        elif len(line) == 4:
            locks.append(line[1])

    return Section(patch_types=patch_types, updates=updates, locks=locks)


def discover_zypper(section: Section) -> type_defs.DiscoveryResult:
    yield Service()


def check_zypper(params: Mapping[str, Any], section: Section) -> CheckResult:
    if section.error:
        yield Result(state=State.UNKNOWN, summary=section.error)
        return

    if section.locks:
        infotext = "%d updates, %d locks" % (section.updates, len(section.locks))
        yield Result(state=State.WARN, summary=infotext)
    else:
        yield Result(state=State.OK, summary="%d updates" % section.updates)

    if section.updates:
        patch_items = sorted(section.patch_types.items())
        for t, c in patch_items:
            infotext = "%s: %d" % (t, c)
            if t == "security":
                yield Result(state=State.CRIT, notice=infotext)
            elif t == "recommended":
                yield Result(state=State.WARN, notice=infotext)
            else:
                yield Result(state=State.OK, notice=infotext)


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
