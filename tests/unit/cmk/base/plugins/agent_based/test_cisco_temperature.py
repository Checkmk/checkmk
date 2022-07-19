#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import cisco_temperature as ct
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


def test_defect_sensor() -> None:
    section = {"8": {"Chassis 1": {"dev_state": (3, "sensor defect"), "raw_dev_state": "1"}}}

    assert list(ct.discover_cisco_temperature(section))

    (defect_result,) = ct.check_cisco_temperature("Chassis 1", {}, section)
    assert isinstance(defect_result, Result)
    assert defect_result.state is not State.OK


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
                ["300000013.1", "2000"],
                ["300000013.2", "-1000"],
                ["300000013.3", "-13904"],
                ["300000013.4", "-9901"],
                ["300000014.1", "1699"],
                ["300000014.2", "-1300"],
                ["300000014.3", "-11301"],
                ["300000014.4", "-7300"],
                ["300003533.1", "2000"],
                ["300003533.2", "-1000"],
                ["300003533.3", "-13904"],
                ["300003533.4", "-9901"],
                ["300003534.1", "1699"],
                ["300003534.2", "-1300"],
                ["300003534.3", "-11301"],
                ["300003534.4", "-7300"],
                ["300005293.1", "2000"],
                ["300005293.2", "-1000"],
                ["300005293.3", "-13904"],
                ["300005293.4", "-9901"],
                ["300005294.1", "1699"],
                ["300005294.2", "-1300"],
                ["300005294.3", "-11301"],
                ["300005294.4", "-7300"],
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
                ["21590.1", "115"],
                ["21590.2", "125"],
                ["21591.1", "115"],
                ["21591.2", "125"],
                ["21592.1", "115"],
                ["21592.2", "125"],
                ["300000003.1", "3630"],
                ["300000003.2", "3465"],
                ["300000003.3", "2970"],
                ["300000003.4", "3135"],
                ["300000004.1", "10500"],
                ["300000004.2", "10500"],
                ["300000004.3", "2500"],
                ["300000004.4", "2500"],
                ["300000007.1", "75000"],
                ["300000007.2", "70000"],
                ["300000007.3", "-5000"],
                ["300000007.4", "0"],
                ["300000013.1", "2000"],
                ["300000013.2", "-1000"],
                ["300000013.3", "-13904"],
                ["300000013.4", "-9901"],
                ["300000014.1", "1699"],
                ["300000014.2", "-1300"],
                ["300000014.3", "-11301"],
                ["300000014.4", "-7300"],
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


def test_check_temp(section_temp: ct.Section) -> None:
    assert list(
        ct.check_cisco_temperature(
            "Ethernet1/1 Lane 1 Transceiver Temperature Sensor", {}, section_temp
        )
    ) == [
        Metric("temp", 24.492, levels=(70.0, 75.0)),
        Result(state=State.OK, summary="Temperature: 24.5°C"),
        Result(state=State.OK, notice="State on device: OK"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]
