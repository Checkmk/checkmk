#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.juniper.agent_based.juniper_fru import check_juniper_fru, discover_juniper_fru
from cmk.plugins.juniper.agent_based.juniper_fru_section import (
    parse_juniper_fru,
    snmp_section_juniper_fru,
)

# SUP-13184
TABLE_DATA_0: StringTable = [
    ["PSM 0", "18", "2"],
    ["PSM 0 INP0", "18", "2"],
    ["PSM 0 INP1", "18", "2"],
    ["PSM 1", "18", "6"],
    ["PSM 1 INP0", "18", "6"],
    ["PSM 1 INP1", "18", "6"],
    ["PSM 2", "18", "6"],
    ["PSM 2 INP0", "18", "6"],
    ["PSM 2 INP1", "18", "6"],
    ["PSM 3", "18", "6"],
    ["PSM 3 INP0", "18", "6"],
    ["PSM 3 INP1", "18", "6"],
    ["PSM 4", "18", "6"],
    ["PSM 4 INP0", "18", "6"],
    ["PSM 4 INP1", "18", "6"],
    ["PSM 5", "18", "6"],
    ["PSM 5 INP0", "18", "6"],
    ["PSM 5 INP1", "18", "6"],
    ["PSM 6", "18", "6"],
    ["PSM 6 INP0", "18", "6"],
    ["PSM 6 INP1", "18", "6"],
    ["PSM 7", "18", "6"],
    ["PSM 7 INP0", "18", "6"],
    ["PSM 7 INP1", "18", "6"],
    ["PSM 8", "18", "2"],
    ["PSM 8 INP0", "18", "2"],
    ["PSM 8 INP1", "18", "2"],
]

# SUP-13184
TABLE_DATA_1: StringTable = [
    ["PEM 0", "7", "6"],
    ["PEM 1", "7", "6"],
    ["PEM 2", "7", "6"],
    ["PEM 3", "7", "6"],
]

# Walk data kept for detection tests
DATA_0: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.2636.1.1.1.2.99",
    ".1.3.6.1.4.1.2636.3.1.15.1.5.22.1.0.0": "PSM 0",
}

DATA_1: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.2636.1.1.1.2.25",
    ".1.3.6.1.4.1.2636.3.1.15.1.5.2.1.0.0": "PEM 0",
}

_SECTION = {
    "Power Supply 0": {"fru_type": "7", "fru_state": "6"},
    "Power Supply 1": {"fru_type": "7", "fru_state": "3"},
    "Fan Tray 0 Fan 0": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 0 Fan 1": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 1 Fan 0": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 1 Fan 1": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 2 Fan 0": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 2 Fan 1": {"fru_type": "13", "fru_state": "6"},
    "FPC: QFX10002-72Q 0": {"fru_type": "3", "fru_state": "6"},
    "PIC: 72X40G 0/0": {"fru_type": "11", "fru_state": "6"},
    "Routing Engine 0": {"fru_type": "6", "fru_state": "6"},
}


def test_parse_juniper_fru() -> None:
    assert (
        parse_juniper_fru(
            [
                ["Power Supply 0", "7", "6"],
                ["Power Supply 1", "7", "3"],
                ["Fan Tray 0 Fan 0", "13", "6"],
                ["Fan Tray 0 Fan 1", "13", "6"],
                ["Fan Tray 1 Fan 0", "13", "6"],
                ["Fan Tray 1 Fan 1", "13", "6"],
                ["Fan Tray 2 Fan 0", "13", "6"],
                ["Fan Tray 2 Fan 1", "13", "6"],
                ["FPC: QFX10002-72Q @ 0/*/*", "3", "6"],
                ["PIC: 72X40G @ 0/0/*", "11", "6"],
                ["Routing Engine 0", "6", "6"],
            ]
        )
        == _SECTION
    )


def test_detect_juniper_fru_with_data_0() -> None:
    assert evaluate_snmp_detection(
        detect_spec=snmp_section_juniper_fru.detect, oid_value_getter=DATA_0.get
    )


def test_detect_juniper_fru_with_data_1() -> None:
    assert evaluate_snmp_detection(
        detect_spec=snmp_section_juniper_fru.detect, oid_value_getter=DATA_1.get
    )


def test_parse_juniper_fru_with_type_7_data() -> None:
    assert snmp_section_juniper_fru.parse_function([TABLE_DATA_1]) == {
        "PEM 0": {"fru_type": "7", "fru_state": "6"},
        "PEM 1": {"fru_type": "7", "fru_state": "6"},
        "PEM 2": {"fru_type": "7", "fru_state": "6"},
        "PEM 3": {"fru_type": "7", "fru_state": "6"},
    }


def test_parse_juniper_fru_with_type_18_data() -> None:
    parsed = snmp_section_juniper_fru.parse_function([TABLE_DATA_0])
    assert parsed is not None
    assert parsed["PSM 0"] == {"fru_type": "18", "fru_state": "2"}
    assert parsed["PSM 1"] == {"fru_type": "18", "fru_state": "6"}
    assert parsed["PSM 8"] == {"fru_type": "18", "fru_state": "2"}


def test_discover_juniper_fru_with_type_7_data() -> None:
    parsed = snmp_section_juniper_fru.parse_function([TABLE_DATA_1])
    assert parsed is not None
    assert list(discover_juniper_fru(parsed)) == [
        Service(item="PEM 0"),
        Service(item="PEM 1"),
        Service(item="PEM 2"),
        Service(item="PEM 3"),
    ]


def test_discover_juniper_fru_with_type_18_data() -> None:
    parsed = snmp_section_juniper_fru.parse_function([TABLE_DATA_0])
    assert parsed is not None
    assert list(discover_juniper_fru(parsed)) == [
        Service(item="PSM 1"),
        Service(item="PSM 1 INP0"),
        Service(item="PSM 1 INP1"),
        Service(item="PSM 2"),
        Service(item="PSM 2 INP0"),
        Service(item="PSM 2 INP1"),
        Service(item="PSM 3"),
        Service(item="PSM 3 INP0"),
        Service(item="PSM 3 INP1"),
        Service(item="PSM 4"),
        Service(item="PSM 4 INP0"),
        Service(item="PSM 4 INP1"),
        Service(item="PSM 5"),
        Service(item="PSM 5 INP0"),
        Service(item="PSM 5 INP1"),
        Service(item="PSM 6"),
        Service(item="PSM 6 INP0"),
        Service(item="PSM 6 INP1"),
        Service(item="PSM 7"),
        Service(item="PSM 7 INP0"),
        Service(item="PSM 7 INP1"),
    ]


def test_check_juniper_fru_online() -> None:
    assert list(check_juniper_fru("Power Supply 0", _SECTION)) == [
        Result(state=State.OK, summary="Operational status: online"),
    ]


def test_check_juniper_fru_present() -> None:
    assert list(check_juniper_fru("Power Supply 1", _SECTION)) == [
        Result(state=State.WARN, summary="Operational status: present"),
    ]


def test_check_juniper_fru_with_type_7_data() -> None:
    parsed = snmp_section_juniper_fru.parse_function([TABLE_DATA_1])
    assert parsed is not None
    assert list(check_juniper_fru("PEM 1", parsed)) == [
        Result(state=State.OK, summary="Operational status: online"),
    ]


def test_check_juniper_fru_with_type_18_data() -> None:
    parsed = snmp_section_juniper_fru.parse_function([TABLE_DATA_0])
    assert parsed is not None
    assert list(check_juniper_fru("PSM 1", parsed)) == [
        Result(state=State.OK, summary="Operational status: online"),
    ]
