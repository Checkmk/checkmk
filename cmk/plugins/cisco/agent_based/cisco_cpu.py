#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1") is depreceated by
# oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"), we recognize both for now


from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    not_contains,
    not_exists,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


@dataclass(frozen=True)
class Section:
    old_oid: str
    new_oid: str


def discover_cisco_cpu(section: Section) -> DiscoveryResult:
    if section.old_oid.isdigit() or section.new_oid.isdigit():
        yield Service()


def check_cisco_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    # Value of section could be (None, None) or ("", "").
    if not section.old_oid.isdigit() and not section.new_oid.isdigit():
        yield Result(
            state=State.UNKNOWN, summary="No information about the CPU utilization available"
        )
        return

    util = float(section.new_oid) if section.new_oid else float(section.old_oid)

    if not isinstance(params, dict):
        params = {"util": params}
    warn, crit = params.get("util", (None, None))

    yield from check_levels(
        util,
        "util",
        (warn, crit),
        human_readable_func=render.percent,
        boundaries=(0, 100),
        infoname="Utilization in the last 5 minutes",
    )


def parse_cisco_cpu(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    return Section(old_oid=string_table[0][0], new_oid=string_table[0][1])


snmp_section_cisco_cpu = SimpleSNMPSection(
    name="cisco_cpu",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        any_of(
            not_contains(".1.3.6.1.2.1.1.1.0", "nx-os"), not_exists(".1.3.6.1.4.1.9.9.305.1.1.1.0")
        ),
        not_exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
        any_of(
            exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"), exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1")
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.109.1.1.1.1",
        oids=["5", "8"],
    ),
    parse_function=parse_cisco_cpu,
)


check_plugin_cisco_cpu = CheckPlugin(
    name="cisco_cpu",
    service_name="CPU utilization",
    discovery_function=discover_cisco_cpu,
    check_function=check_cisco_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
