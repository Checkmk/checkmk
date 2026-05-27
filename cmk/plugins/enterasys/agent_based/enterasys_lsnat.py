#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)


def _saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_enterasys_lsnat(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_enterasys_lsnat(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_enterasys_lsnat(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section:
        return

    raw_levels = params.get("current_bindings")
    yield from check_levels(
        _saveint(section[0][0]),
        metric_name="current_bindings",
        levels_upper=("fixed", raw_levels) if raw_levels is not None else None,
        label="Current bindings",
        render_func=lambda x: str(int(x)),
    )


snmp_section_enterasys_lsnat = SimpleSNMPSection(
    name="enterasys_lsnat",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5624.2.1"),
        exists(".1.3.6.1.4.1.5624.1.2.74.1.1.5.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5624.1.2.74.1.1.5",
        oids=["0"],
    ),
    parse_function=parse_enterasys_lsnat,
)


check_plugin_enterasys_lsnat = CheckPlugin(
    name="enterasys_lsnat",
    service_name="LSNAT Bindings",
    discovery_function=discover_enterasys_lsnat,
    check_function=check_enterasys_lsnat,
    check_ruleset_name="lsnat",
    check_default_parameters={
        "current_bindings": None,
    },
)
