#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.plugins.cisco_sma.agent_based.detect import DETECT_CISCO_SMA_SNMP
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


class Params(TypedDict):
    levels_upper: SimpleLevelsConfigModel[float]
    levels_lower: SimpleLevelsConfigModel[float]


def _check_mail_transfer_threads(params: Params, section: int) -> CheckResult:
    yield from check_levels(
        section,
        label="Total",
        render_func=lambda x: str(int(x)),
        metric_name="cisco_sma_mail_transfer_threads",
        levels_upper=params["levels_upper"],
        levels_lower=params["levels_lower"],
    )


def _discover_mail_transfer_threads(section: int) -> DiscoveryResult:
    yield Service()


check_plugin_mail_transfer_threads = CheckPlugin(
    name="cisco_sma_mail_transfer_threads",
    service_name="Mail transfer threads",
    discovery_function=_discover_mail_transfer_threads,
    check_function=_check_mail_transfer_threads,
    check_ruleset_name="generic_numeric_value_without_item",
    check_default_parameters=Params(
        levels_upper=("fixed", (500.0, 1000.0)),
        levels_lower=("no_levels", None),
    ),
)


def _parse_mail_transfer_threads(string_table: StringTable) -> int | None:
    if not string_table or not string_table[0]:
        return None

    return int(string_table[0][0])


snmp_section_mail_transfer_threads = SimpleSNMPSection(
    parsed_section_name="cisco_sma_mail_transfer_threads",
    name="cisco_sma_mail_transfer_threads",
    detect=DETECT_CISCO_SMA_SNMP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["20"],
    ),
    parse_function=_parse_mail_transfer_threads,
)
