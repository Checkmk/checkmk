#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based.checking_classes import CheckResult
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based import cisco_temperature as ct
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    ["input_table", "expected_section"],
    [
        pytest.param(
            [
                [["1010", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    ["1010.1", "20", "4", "56"],
                    ["1010.2", "10", "4", "46"],
                    ["1010.3", "20", "2", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["description", "1"]],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor 1010": {"obsolete": True},
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (46.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="Both upper thresholds",
        ),
        pytest.param(
            [
                [["1010", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    ["1010.1", "20", "4", "56"],
                    ["1010.2", "10", "2", "46"],
                    ["1010.3", "20", "2", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["description", "1"]],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor 1010": {"obsolete": True},
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (56.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="Only 1 upper threshold",
        ),
        pytest.param(
            [
                [["1132", "TenGigabitEthernet1/1/7 Transmit Power Sensor"]],
                [["1132", "14", "9", "1", "-19", "2"]],
                [],
                [],
                [],
            ],
            {
                "14": {
                    "TenGigabitEthernet1/1/7 Transmit Power Sensor": {
                        "admin_state": None,
                        "descr": "TenGigabitEthernet1/1/7 " "Transmit " "Power " "Sensor",
                        "dev_state": (3, "unavailable"),
                        "raw_dev_state": "2",
                    }
                },
                "8": {},
            },
            id="Defect sensor",
        ),
        pytest.param(
            [
                [["1010", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    # threshold relations not applicable to check_levels:
                    # 3 -> greater than, 2 -> less or equal
                    ["1010.1", "20", "3", "76"],
                    ["1010.2", "10", "3", "66"],
                    ["1010.3", "20", "2", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["description", "1"]],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor 1010": {"obsolete": True},
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (56.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="EnvMon threshold fallback",
        ),
    ],
)
def test_parse_cisco_temperature_thresholds(
    input_table: list[StringTable], expected_section: ct.Section
) -> None:
    assert ct.parse_cisco_temperature(input_table) == expected_section


def test_defect_sensor() -> None:
    section = {"8": {"Chassis 1": {"dev_state": (3, "sensor defect"), "raw_dev_state": "1"}}}

    assert list(ct.discover_cisco_temperature(section))

    (defect_result,) = ct.check_cisco_temperature("Chassis 1", {}, section)
    assert isinstance(defect_result, Result)
    assert defect_result.state is not State.OK


@pytest.fixture(name="section_not_ok_sensors", scope="module")
def _section_not_ok_sensors() -> ct.Section:
    return ct.parse_cisco_temperature(
        [
            [
                ["1107", "TenGigabitEthernet2/1/7 Module Temperature Sensor"],
                ["1110", "TenGigabitEthernet2/1/7 Transmit Power Sensor"],
                ["1111", "TenGigabitEthernet2/1/7 Receive Power Sensor"],
                ["1129", "TenGigabitEthernet1/1/7 Module Temperature Sensor"],
                ["1132", "TenGigabitEthernet1/1/7 Transmit Power Sensor"],
                ["1133", "TenGigabitEthernet1/1/7 Receive Power Sensor"],
            ],
            [
                ["1107", "8", "9", "1", "245", "3"],
                ["1110", "14", "9", "1", "-19", "3"],
                ["1111", "14", "9", "1", "-47", "3"],
                ["1129", "8", "9", "1", "245", "2"],
                ["1132", "14", "9", "1", "-19", "2"],
                ["1133", "14", "9", "1", "-47", "2"],
            ],
            [],
            [],
            [],
        ],
    )


@pytest.fixture(name="section_dom", scope="module")
def _get_secion_dom() -> ct.Section:
    return ct.parse_cisco_temperature(
        [
            [
                ["300000013", "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor"],
                ["300000014", "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor"],
                ["300003533", "Ethernet1/3 Lane 1 Transceiver Receive Power Sensor"],
                ["300003534", "Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor"],
                ["300005293", "Ethernet1/4 Lane 1 Transceiver Receive Power Sensor"],
                ["300005294", "Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor"],
            ],
            [
                ["300000013", "14", "8", "0", "-3271", "1"],
                ["300000014", "14", "8", "0", "1000", "1"],
                ["300003533", "14", "8", "0", "-2823", "1"],
                ["300003534", "14", "8", "0", "-1000", "1"],
                ["300005293", "14", "8", "0", "-40000", "1"],
                ["300005294", "14", "8", "0", "0", "1"],
            ],
            [
                ["300000013.1", "20", "3", "2000"],
                ["300000013.2", "10", "3", "-1000"],
                ["300000013.3", "20", "1", "-13904"],
                ["300000013.4", "10", "1", "-9901"],
                ["300000014.1", "20", "3", "1699"],
                ["300000014.2", "10", "3", "-1300"],
                ["300000014.3", "20", "1", "-11301"],
                ["300000014.4", "10", "1", "-7300"],
                ["300003533.1", "20", "3", "2000"],
                ["300003533.2", "10", "3", "-1000"],
                ["300003533.3", "20", "1", "-13904"],
                ["300003533.4", "10", "1", "-9901"],
                ["300003534.1", "20", "3", "1699"],
                ["300003534.2", "10", "3", "-1300"],
                ["300003534.3", "20", "1", "-11301"],
                ["300003534.4", "10", "1", "-7300"],
                ["300005293.1", "20", "3", "2000"],
                ["300005293.2", "10", "3", "-1000"],
                ["300005293.3", "20", "1", "-13904"],
                ["300005293.4", "10", "1", "-9901"],
                ["300005294.1", "20", "3", "1699"],
                ["300005294.2", "10", "3", "-1300"],
                ["300005294.3", "20", "1", "-11301"],
                ["300005294.4", "10", "1", "-7300"],
            ],
            [],
            [
                ["Ethernet1/1 Lane 1 Transceiver Receive Power Sensor", "1"],
                ["Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor", "1"],
                ["Ethernet1/3 Lane 1 Transceiver Receive Power Sensor", "2"],
                ["Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor", "2"],
                ["Ethernet1/4 Lane 1 Transceiver Receive Power Sensor", "3"],
                ["Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor", "3"],
            ],
        ]
    )


def test_discovery_dom(section_dom: ct.Section) -> None:
    assert not list(ct.discover_cisco_temperature(section_dom))

    assert sorted(
        ct.discover_cisco_temperature_dom({"admin_states": ["1", "3"]}, section_dom)
    ) == sorted(
        [
            Service(item="Ethernet1/1 Lane 1 Transceiver Receive Power Sensor"),
            Service(item="Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor"),
            Service(item="Ethernet1/4 Lane 1 Transceiver Receive Power Sensor"),
            Service(item="Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor"),
        ]
    )


def test_discovery_not_ok_sensors(section_not_ok_sensors: ct.Section) -> None:
    assert not list(ct.discover_cisco_temperature(section_not_ok_sensors))
    assert not list(
        ct.discover_cisco_temperature_dom({"admin_states": ["1", "3"]}, section_not_ok_sensors)
    )


def test_check_dom_good_default(section_dom: ct.Section) -> None:
    assert list(
        ct.check_cisco_temperature_dom(
            "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor",
            {},
            section_dom,
        )
    ) == [
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Signal power: -3.27 dBm"),
        Metric("input_signal_power_dbm", -3.271, levels=(-1.0, 2.0)),
    ]


def test_check_dom_no_levels() -> None:
    assert list(
        ct.check_cisco_temperature_dom(
            "NoLevels",
            {},
            {
                "14": {
                    "NoLevels": {
                        "descr": "",
                        "reading": 3.14,
                        "raw_dev_state": "1",
                        "dev_state": (0, "awesome"),
                        "dev_levels": None,
                    }
                }
            },
        )
    ) == [
        Result(state=State.OK, summary="Status: awesome"),
        Result(state=State.OK, summary="Signal power: 3.14 dBm"),
        Metric("signal_power_dbm", 3.14),
    ]


@pytest.fixture(name="section_temp", scope="module")
def _get_secion_temp() -> ct.Section:
    return ct.parse_cisco_temperature(
        [
            [
                ["1176", "Filtered sensor"],
                ["1177", "Sensor with large precision"],
                ["2008", "Switch 1 - WS-C2960X-24PD-L - Sensor 0"],
                ["4950", "Linecard-1 Port-1"],
                ["21590", "module-1 Crossbar1(s1)"],
                ["21591", "module-1 Crossbar2(s2)"],
                ["21592", "module-1 Arb-mux (s3)"],
                ["31958", "Transceiver(slot:1-port:1)"],
                ["300000003", "Ethernet1/1 Lane 1 Transceiver Voltage Sensor"],
                ["300000004", "Ethernet1/1 Lane 1 Transceiver Bias Current Sensor"],
                ["300000007", "Ethernet1/1 Lane 1 Transceiver Temperature Sensor"],
                ["300000013", "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor"],
                ["300000014", "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor"],
            ],
            [
                ["1176", "1", "9", "1613258611", "0", "1"],
                ["1177", "8", "9", "1613258611", "0", "1"],
                ["21590", "8", "9", "0", "62", "1"],
                ["21591", "8", "9", "0", "58", "1"],
                ["21592", "8", "9", "0", "49", "1"],
                ["300000003", "4", "8", "0", "3333", "1"],
                ["300000004", "5", "7", "0", "6002", "1"],
                ["300000007", "8", "8", "0", "24492", "1"],
                ["300000013", "14", "8", "0", "-3271", "1"],
                ["300000014", "14", "8", "0", "1000", "1"],
            ],
            [
                ["21590.1", "10", "4", "115"],
                ["21590.2", "20", "4", "125"],
                ["21591.1", "10", "4", "115"],
                ["21591.2", "20", "4", "125"],
                ["21592.1", "10", "4", "115"],
                ["21592.2", "20", "4", "125"],
                ["300000003.1", "10", "4", "3630"],
                ["300000003.2", "20", "4", "3465"],
                ["300000003.3", "10", "1", "2970"],
                ["300000003.4", "20", "1", "3135"],
                ["300000004.1", "10", "4", "10500"],
                ["300000004.2", "20", "4", "10500"],
                ["300000004.3", "10", "1", "2500"],
                ["300000004.4", "20", "1", "2500"],
                ["300000007.1", "10", "4", "70000"],
                ["300000007.2", "20", "4", "75000"],
                ["300000007.3", "10", "1", "-5000"],
                ["300000007.4", "20", "1", "0"],
                ["300000013.1", "10", "4", "2000"],
                ["300000013.2", "20", "4", "-1000"],
                ["300000013.3", "10", "1", "-13904"],
                ["300000013.4", "20", "1", "-9901"],
                ["300000014.1", "10", "4", "1699"],
                ["300000014.2", "20", "4", "-1300"],
                ["300000014.3", "10", "1", "-11301"],
                ["300000014.4", "20", "1", "-7300"],
            ],
            [
                ["2008", "SW#1, Sensor#1, GREEN", "36", "68", "1"],
                ["3008", "SW#2, Sensor#1, GREEN", "37", "68", "1"],
            ],
            [],
        ]
    )


def test_discovery_temp(section_temp: ct.Section) -> None:
    assert sorted(ct.discover_cisco_temperature(section_temp)) == sorted(
        [
            Service(item="Sensor with large precision"),
            Service(item="Ethernet1/1 Lane 1 Transceiver Temperature Sensor"),
            Service(item="SW 1 Sensor 1"),
            Service(item="SW 2 Sensor 1"),
            Service(item="module-1 Arb-mux (s3)"),
            Service(item="module-1 Crossbar1(s1)"),
            Service(item="module-1 Crossbar2(s2)"),
        ]
    )


@pytest.mark.usefixtures("initialised_item_state")
def test_check_temp(section_temp: ct.Section) -> None:
    assert list(
        ct.check_cisco_temperature(
            "Ethernet1/1 Lane 1 Transceiver Temperature Sensor", {}, section_temp
        )
    ) == [
        Metric("temp", 24.492, levels=(70.0, 75.0)),
        Result(state=State.OK, summary="Temperature: 24.5 °C"),
        Result(state=State.OK, notice="State on device: OK"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "TenGigabitEthernet1/1/7 Module Temperature Sensor",
            [Result(state=State.UNKNOWN, notice="Status: unavailable")],
        ),
        pytest.param(
            "TenGigabitEthernet2/1/7 Module Temperature Sensor",
            [Result(state=State.CRIT, notice="Status: non-operational")],
        ),
    ],
)
def test_check_temp_not_ok_sensors(
    item: str, expected_result: CheckResult, section_not_ok_sensors: ct.Section
) -> None:
    assert list(ct.check_cisco_temperature(item, {}, section_not_ok_sensors)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "TenGigabitEthernet1/1/7 Transmit Power Sensor",
            [Result(state=State.UNKNOWN, notice="Status: unavailable")],
        ),
        pytest.param(
            "TenGigabitEthernet2/1/7 Transmit Power Sensor",
            [Result(state=State.CRIT, notice="Status: non-operational")],
        ),
    ],
)
def test_check_dom_not_ok_sensors(
    item: str, expected_result: CheckResult, section_not_ok_sensors: ct.Section
) -> None:
    assert list(ct.check_cisco_temperature_dom(item, {}, section_not_ok_sensors)) == expected_result
