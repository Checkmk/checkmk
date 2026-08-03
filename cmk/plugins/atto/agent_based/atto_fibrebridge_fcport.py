#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def parse_atto_fibrebridge_fcport(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_atto_fibrebridge_fcport = SimpleSNMPSection(
    name="atto_fibrebridge_fcport",
    parse_function=parse_atto_fibrebridge_fcport,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4547"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4547.2.3.3.2.1",
        oids=[OIDEnd(), "2", "3"],
    ),
)


def discover_atto_fibrebridge_fcport(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_atto_fibrebridge_fcport(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    now = time.time()
    fc_tx_words: float | None = None
    fc_rx_words: float | None = None
    for line in section:
        if line[0] == item:
            fc_tx_words = get_rate(get_value_store(), "tx", now, int(line[1]), raise_overflow=True)
            fc_rx_words = get_rate(get_value_store(), "rx", now, int(line[2]), raise_overflow=True)

    if fc_tx_words is None or fc_rx_words is None:
        return

    if not params["fc_tx_words"]:
        yield Result(state=State.OK, summary=f"TX: {fc_tx_words:.2f} words/s")
        yield Metric("fc_tx_words", fc_tx_words)
    else:
        yield from check_levels(
            fc_tx_words,
            metric_name="fc_tx_words",
            levels_upper=("fixed", params["fc_tx_words"]),
            label="TX",
        )

    if not params["fc_rx_words"]:
        yield Result(state=State.OK, summary=f"RX: {fc_rx_words:.2f} words/s")
        yield Metric("fc_rx_words", fc_rx_words)
    else:
        yield from check_levels(
            fc_rx_words,
            metric_name="fc_rx_words",
            levels_upper=("fixed", params["fc_rx_words"]),
            label="RX",
        )


check_plugin_atto_fibrebridge_fcport = CheckPlugin(
    name="atto_fibrebridge_fcport",
    service_name="FC Port %s",
    discovery_function=discover_atto_fibrebridge_fcport,
    check_function=check_atto_fibrebridge_fcport,
    check_ruleset_name="fcport_words",
    check_default_parameters={
        "fc_tx_words": None,
        "fc_rx_words": None,
    },
)
