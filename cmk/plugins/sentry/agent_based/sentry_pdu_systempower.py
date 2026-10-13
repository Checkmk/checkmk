#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

# .1.3.6.1.4.1.1718.3.1.6.0 2111

Section = Mapping[str, ElPhase]


def parse_sentry_pdu_systempower(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    return {"Power Supply System": ElPhase(power=ReadingWithState(value=int(string_table[0][0])))}


def discover_sentry_pdu_systempower(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_sentry_pdu_systempower(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_sentry_pdu_systempower = SimpleSNMPSection(
    name="sentry_pdu_systempower",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.3.1",
        oids=["6"],
    ),
    parse_function=parse_sentry_pdu_systempower,
)


check_plugin_sentry_pdu_systempower = CheckPlugin(
    name="sentry_pdu_systempower",
    service_name="%s",
    discovery_function=discover_sentry_pdu_systempower,
    check_function=check_sentry_pdu_systempower,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
