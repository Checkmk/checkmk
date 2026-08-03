#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# docsIfCmStatusValue                         1.3.6.1.2.1.10.127.1.2.2.1.1
# docsIfCmStatusT1Timeouts                    1.3.6.1.2.1.10.127.1.2.2.1.10
# docsIfCmStatusT2Timeouts                    1.3.6.1.2.1.10.127.1.2.2.1.11
# docsIfCmStatusT3Timeouts                    1.3.6.1.2.1.10.127.1.2.2.1.12
# docsIfCmStatusT4Timeouts                    1.3.6.1.2.1.10.127.1.2.2.1.13
# docsIfCmStatusRangingAborteds               1.3.6.1.2.1.10.127.1.2.2.1.14
# docsIfCmStatusDocsisOperMode                1.3.6.1.2.1.10.127.1.2.2.1.15
# docsIfCmStatusModulationType                1.3.6.1.2.1.10.127.1.2.2.1.16
# docsIfCmStatusCode                          1.3.6.1.2.1.10.127.1.2.2.1.2
# docsIfCmStatusTxPower                       1.3.6.1.2.1.10.127.1.2.2.1.3
# docsIfCmStatusResets                        1.3.6.1.2.1.10.127.1.2.2.1.4
# docsIfCmStatusLostSyncs                     1.3.6.1.2.1.10.127.1.2.2.1.5
# docsIfCmStatusInvalidMaps                   1.3.6.1.2.1.10.127.1.2.2.1.6
# docsIfCmStatusInvalidUcds                   1.3.6.1.2.1.10.127.1.2.2.1.7
# docsIfCmStatusInvalidRangingResponses       1.3.6.1.2.1.10.127.1.2.2.1.8
# docsIfCmStatusInvalidRegistrationResponses  1.3.6.1.2.1.10.127.1.2.2.1.9


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

_STATE_MAP = {0: State.OK, 1: State.WARN, 2: State.CRIT, 3: State.UNKNOWN}


def discover_docsis_cm_status(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_docsis_cm_status(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    status_table = {
        1: "other",
        2: "not ready",
        3: "not synchronized",
        4: "PHY synchronized",
        5: "upstream parameters acquired",
        6: "ranging complete",
        7: "IP complete",
        8: "TOD established",
        9: "security established",
        10: "params transfer complete",
        11: "registration complete",
        12: "operational",
        13: "access denied",
    }

    for sid, status, tx_power in section:
        if sid == item:
            # Modem Status
            status_int = int(status)
            infotext = f"Status: {status_table[status_int]}"
            state = State.CRIT if status_int in params["error_states"] else State.OK
            yield Result(state=state, summary=infotext)

            # TX Power
            tx_power_dbmv = float(tx_power) / 10
            warn, crit = params["tx_power"]
            levels = f" (warn/crit at {warn:.1f}/{crit:.1f} dBmV)"
            state = State.OK
            infotext = f"TX Power is {tx_power_dbmv:.1f} dBmV"
            if tx_power_dbmv <= crit:
                state = State.CRIT
                infotext += levels
            elif tx_power_dbmv <= warn:
                state = State.WARN
                infotext += levels
            yield Result(state=state, summary=infotext)
            yield Metric("tx_power", tx_power_dbmv, levels=(warn, crit))
            return

        yield Result(state=State.UNKNOWN, summary="Status Entry not found")


def parse_docsis_cm_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_docsis_cm_status = SimpleSNMPSection(
    name="docsis_cm_status",
    parse_function=parse_docsis_cm_status,
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4115.820.1.0.0.0.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4115.900.2.0.0.0.0.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.10.127.1.2.2.1",
        oids=[OIDEnd(), "1", "3"],
    ),
)

check_plugin_docsis_cm_status = CheckPlugin(
    name="docsis_cm_status",
    service_name="Cable Modem %s Status",
    discovery_function=discover_docsis_cm_status,
    check_function=check_docsis_cm_status,
    check_ruleset_name="docsis_cm_status",
    check_default_parameters={
        "tx_power": (20.0, 10.0),
        "error_states": [13, 2, 1],
    },
)
