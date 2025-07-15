#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.agent_based.v1 import Metric, Result, State
from cmk.agent_based.v1.type_defs import CheckResult
from cmk.plugins.collection.agent_based.apc_ats_output import (
    check_apc_ats_output,
    DefaultParameters,
    Section,
    snmp_section_apc_ats_output,
)
from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)


@pytest.mark.parametrize(
    ["input_table", "expected_section"],
    [
        pytest.param(
            """
.1.3.6.1.2.1.1.1.0 APC Web/SNMP Management Card (MB:v4.1.0 PF:v6.9.6 PN:apc_hw05_aos_696.bin AF1:v6.9.6 AN1:apc_hw05_ats4g_696.bin MN:AP4421 HR:R01 SN: 5A2143T95739 MD:10/31/2021)
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.318.1.3.32
.1.3.6.1.2.1.1.3.0 326564370
.1.3.6.1.2.1.1.4.0 Unknown
.1.3.6.1.2.1.1.5.0 ATS003-VIEHQ-O17-2
.1.3.6.1.2.1.1.6.0 Network Room O17.298
.1.3.6.1.2.1.1.7.0 72
.1.3.6.1.2.1.1.8.0 0
.1.3.6.1.2.1.1.9.1.2.1 .1.3.6.1.6.3.1
.1.3.6.1.2.1.1.9.1.2.2 .1.3.6.1.6.3.10.3.1.1
.1.3.6.1.2.1.1.9.1.2.3 .1.3.6.1.6.3.11.3.1.1
.1.3.6.1.2.1.1.9.1.2.4 .1.3.6.1.6.3.15.2.1.1
.1.3.6.1.2.1.1.9.1.2.5 .1.3.6.1.6.3.16.2.1.1
.1.3.6.1.2.1.1.9.1.3.1 The MIB Module from SNMPv2 entities
.1.3.6.1.2.1.1.9.1.3.2 SNMP Management Architecture MIB
.1.3.6.1.2.1.1.9.1.3.3 Message Processing and Dispatching MIB
.1.3.6.1.2.1.1.9.1.3.4 USM User MIB
.1.3.6.1.2.1.1.9.1.3.5 VACM MIB
.1.3.6.1.2.1.1.9.1.4.1 0
.1.3.6.1.4.1.318.1.1.8.5.4.2.1.1.1 1
.1.3.6.1.4.1.318.1.1.8.5.4.2.1.2.1 1
.1.3.6.1.4.1.318.1.1.8.5.4.2.1.3.1 2
.1.3.6.1.4.1.318.1.1.8.5.4.2.1.4.1 50
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.1.1.1.1 1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.2.1.1.1 1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.3.1.1.1 230
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.4.1.1.1 10
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.5.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.6.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.7.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.8.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.9.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.10.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.11.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.12.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.13.1.1.1 230
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.14.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.15.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.16.1.1.1 10
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.17.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.18.1.1.1 -1
.1.3.6.1.4.1.318.1.1.8.5.4.3.1.19.1.1.1 1
""",
            {
                "1": {
                    "voltage": 230.0,
                    "current": 1.0,
                    "perc_load": -1.0,
                    "power": 230.0,
                },
            },
            id="Catalyst",
        ),
    ],
)
def test_parse_snmp_section(
    input_table: str,
    expected_section: Section,
    as_path: Callable[[str], Path],
) -> None:
    snmp_walk = as_path(input_table)

    assert snmp_is_detected(snmp_section_apc_ats_output, snmp_walk)

    assert expected_section == get_parsed_snmp_section(snmp_section_apc_ats_output, snmp_walk)


@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "1",
            {},
            [
                Result(state=State.OK, summary="Voltage: 230.00 V"),
                Metric("volt", 230.0),
                Result(state=State.OK, summary="Power: 230.00 W"),
                Metric("watt", 230.0),
                Result(state=State.OK, summary="Current: 1.00 A"),
                Metric("current", 1.0),
                Result(state=State.OK, summary="Load: 1.00%"),
                Metric("load_perc", 1.0),
            ],
            id="No param",
        ),
        pytest.param(
            "1",
            {"output_voltage_max": ("fixed", (120, 240))},
            [
                Result(
                    state=State.WARN, summary="Voltage: 230.00 V (warn/crit at 120.00 V/240.00 V)"
                ),
                Metric("volt", 230.0, levels=(120, 240)),
                Result(state=State.OK, summary="Power: 230.00 W"),
                Metric("watt", 230.0),
                Result(state=State.OK, summary="Current: 1.00 A"),
                Metric("current", 1.0),
                Result(state=State.OK, summary="Load: 1.00%"),
                Metric("load_perc", 1.0),
            ],
            id="Upper level for voltage",
        ),
        pytest.param(
            "1",
            {
                "output_voltage_max": ("fixed", (120, 240)),
                "output_voltage_min": ("fixed", (10, 20)),
            },
            [
                Result(
                    state=State.WARN, summary="Voltage: 230.00 V (warn/crit at 120.00 V/240.00 V)"
                ),
                Metric("volt", 230.0, levels=(120, 240)),
                Result(state=State.OK, summary="Power: 230.00 W"),
                Metric("watt", 230.0),
                Result(state=State.OK, summary="Current: 1.00 A"),
                Metric("current", 1.0),
                Result(state=State.OK, summary="Load: 1.00%"),
                Metric("load_perc", 1.0),
            ],
            id="Upper level for voltage",
        ),
        pytest.param(
            "1",
            {
                "output_current_max": ("fixed", (1, 3)),
            },
            [
                Result(state=State.OK, summary="Voltage: 230.00 V"),
                Metric("volt", 230.0),
                Result(state=State.OK, summary="Power: 230.00 W"),
                Metric("watt", 230.0),
                Result(state=State.WARN, summary="Current: 1.00 A (warn/crit at 1.00 A/3.00 A)"),
                Metric("current", 1.0, levels=(1, 3)),
                Result(state=State.OK, summary="Load: 1.00%"),
                Metric("load_perc", 1.0),
            ],
            id="Upper level for current",
        ),
        pytest.param(
            "1",
            {
                "output_power_max": ("fixed", (230, 300)),
            },
            [
                Result(state=State.OK, summary="Voltage: 230.00 V"),
                Metric("volt", 230.0),
                Result(
                    state=State.WARN, summary="Power: 230.00 W (warn/crit at 230.00 W/300.00 W)"
                ),
                Metric("watt", 230.0, levels=(230, 300)),
                Result(state=State.OK, summary="Current: 1.00 A"),
                Metric("current", 1.0),
                Result(state=State.OK, summary="Load: 1.00%"),
                Metric("load_perc", 1.0),
            ],
            id="Upper level for power",
        ),
        pytest.param(
            "1",
            {"load_perc_min": ("fixed", (10.0, 12.0))},
            [
                Result(state=State.OK, summary="Voltage: 230.00 V"),
                Metric("volt", 230.0),
                Result(state=State.OK, summary="Power: 230.00 W"),
                Metric("watt", 230.0),
                Result(state=State.OK, summary="Current: 1.00 A"),
                Metric("current", 1.0),
                Result(state=State.CRIT, summary="Load: 1.00% (warn/crit below 10.00%/12.00%)"),
                Metric("load_perc", 1.0),
            ],
            id="Lower level for load",
        ),
        pytest.param(
            "2",
            {},
            [
                Result(state=State.OK, summary="Voltage: 230.00 V"),
                Metric("volt", 230.0),
                Result(state=State.OK, summary="Power: 230.00 W"),
                Metric("watt", 230.0),
                Result(state=State.OK, summary="Current: 1.00 A"),
                Metric("current", 1.0),
            ],
            id="Load not supported",
        ),
    ],
)
def test_check_dom_not_ok_sensors(
    item: str, params: DefaultParameters, expected_result: CheckResult
) -> None:
    section: Section = {
        "1": {
            "voltage": 230.0,
            "current": 1.0,
            "perc_load": 1.0,
            "power": 230.0,
        },
        "2": {
            "voltage": 230.0,
            "current": 1.0,
            "perc_load": -1.0,
            "power": 230.0,
        },
    }

    result = list(check_apc_ats_output(item, params, section))
    assert result == expected_result
