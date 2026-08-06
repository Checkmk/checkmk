#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.domino.lib import DETECT
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


def discover_domino_transactions(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


class DominoTransactionsParams(TypedDict):
    levels: SimpleLevelsConfigModel[int]


def check_domino_transactions(
    params: DominoTransactionsParams, section: StringTable
) -> CheckResult:
    if section:
        yield from check_levels(
            int(section[0][0]),
            levels_upper=params["levels"],
            metric_name="transactions",
            render_func=str,
            label="Transactions per minute (avg)",
        )


def parse_domino_transactions(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_domino_transactions = SimpleSNMPSection(
    name="domino_transactions",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.6.3",
        oids=["2"],
    ),
    parse_function=parse_domino_transactions,
)


check_plugin_domino_transactions = CheckPlugin(
    name="domino_transactions",
    service_name="Domino Server Transactions",
    discovery_function=discover_domino_transactions,
    check_function=check_domino_transactions,
    check_ruleset_name="domino_transactions",
    check_default_parameters=DominoTransactionsParams(levels=("fixed", (30000, 35000))),
)
