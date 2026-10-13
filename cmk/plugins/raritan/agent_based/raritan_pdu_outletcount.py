#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)


def discover_raritan_pdu_outletcount(section: StringTable) -> DiscoveryResult:
    if section and section[0]:
        yield Service()


def check_raritan_pdu_outletcount(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    with contextlib.suppress(IndexError):
        yield from check_levels_v1(
            int(section[0][0]),
            metric_name="outletcount",
            levels_upper=params.get("levels_upper"),
            levels_lower=params.get("levels_lower"),
            render_func=lambda f: "%.f" % f,
        )


def parse_raritan_pdu_outletcount(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_raritan_pdu_outletcount = SimpleSNMPSection(
    name="raritan_pdu_outletcount",
    parse_function=parse_raritan_pdu_outletcount,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
        any_of(
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX2-2"),
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX3"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.2.2.1.4",
        oids=["1"],
    ),
)


check_plugin_raritan_pdu_outletcount = CheckPlugin(
    name="raritan_pdu_outletcount",
    service_name="Outlet Count",
    discovery_function=discover_raritan_pdu_outletcount,
    check_function=check_raritan_pdu_outletcount,
    check_ruleset_name="plug_count",
    check_default_parameters={},
)
