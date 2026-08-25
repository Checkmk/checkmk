#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.hp_hh3c.agent_based import hp_hh3c_ext
from cmk.plugins.hp_hh3c.agent_based.hp_hh3c_ext import (
    check_hp_hh3c_ext,
    check_hp_hh3c_ext_cpu,
    check_hp_hh3c_ext_mem,
    check_hp_hh3c_ext_states,
    discover_hp_hh3c_ext,
    discover_hp_hh3c_ext_cpu,
    discover_hp_hh3c_ext_mem,
    discover_hp_hh3c_ext_states,
    parse_hp_hh3c_ext,
    snmp_section_hp_hh3c_ext,
)
from cmk.plugins.hp_hh3c.lib import OID_SysObjectID

_STATE_ENTRY_OID = ".1.3.6.1.4.1.25506.2.6.1.1.1.1.*"

_INVALID_TEMPERATURE = "65535"

_MEM_TOTAL = 1073741824
_TEMPERATURE = 42

# hh3cEntityExtStateEntry columns: index, admin, oper, CPU usage, memory usage, temperature,
# memory size.
_STRING_TABLE = [
    [
        ["1", "2", "3", "0", "0", _INVALID_TEMPERATURE, "0"],
        ["192", "2", "3", "8", "39", str(_TEMPERATURE), str(_MEM_TOTAL)],
        ["432", "2", "3", "0", "0", _INVALID_TEMPERATURE, "0"],
    ],
    [
        ["1", "HPE"],
        ["192", "MODULE LEVEL1"],
        ["432", "MODULE LEVEL2"],
    ],
]

_ITEM = "MODULE LEVEL1 192"


@pytest.mark.parametrize(
    "oid_data",
    [
        pytest.param(
            {OID_SysObjectID: ".1.3.6.1.4.1.25506.11.1.290", _STATE_ENTRY_OID: "0"},
            id="HPE 5710 24XGT 6QS+/2QS28",
        ),
        pytest.param(
            {OID_SysObjectID: ".1.3.6.1.4.1.25506.11.1.239", _STATE_ENTRY_OID: "0"},
            id="formerly allow-listed .239",
        ),
        pytest.param(
            {OID_SysObjectID: ".1.3.6.1.4.1.25506.11.1.189", _STATE_ENTRY_OID: "0"},
            id="formerly allow-listed .189",
        ),
        pytest.param(
            {OID_SysObjectID: ".1.3.6.1.4.1.25506.11.1.87", _STATE_ENTRY_OID: "0"},
            id="formerly allow-listed .87",
        ),
    ],
)
def test_detect_hp_hh3c_ext_matches(oid_data: Mapping[str, str]) -> None:
    assert evaluate_snmp_detection(
        detect_spec=snmp_section_hp_hh3c_ext.detect,
        oid_value_getter=oid_data.get,
    )


@pytest.mark.parametrize(
    "oid_data",
    [
        pytest.param(
            {OID_SysObjectID: ".1.3.6.1.4.1.25506.11.1.290"},
            id="H3C device without HH3C-ENTITY-EXT MIB",
        ),
        pytest.param(
            {OID_SysObjectID: ".1.3.6.1.4.1.9.1.1745", _STATE_ENTRY_OID: "0"},
            id="other vendor",
        ),
    ],
)
def test_detect_hp_hh3c_ext_does_not_match(oid_data: Mapping[str, str]) -> None:
    assert not evaluate_snmp_detection(
        detect_spec=snmp_section_hp_hh3c_ext.detect,
        oid_value_getter=oid_data.get,
    )


def test_parse_hp_hh3c_ext_without_state_table() -> None:
    # The former detection fired on three sysObjectIDs alone. Requiring the table on top of
    # that discovers no less: without it there is nothing to discover from either.
    assert not parse_hp_hh3c_ext([[], []])


def test_discover_hp_hh3c_ext() -> None:
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(discover_hp_hh3c_ext(section)) == [Service(item=_ITEM)]


def test_discover_hp_hh3c_ext_states() -> None:
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(discover_hp_hh3c_ext_states(section)) == [Service(item=_ITEM)]


def test_discover_hp_hh3c_ext_cpu() -> None:
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(discover_hp_hh3c_ext_cpu(section)) == [Service(item=_ITEM)]


def test_discover_hp_hh3c_ext_mem() -> None:
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(discover_hp_hh3c_ext_mem(section)) == [Service(item=_ITEM)]


def test_check_hp_hh3c_ext(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hp_hh3c_ext, "get_value_store", dict)
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(check_hp_hh3c_ext(_ITEM, {}, section)) == [
        Metric("temp", float(_TEMPERATURE)),
        Result(state=State.OK, summary=f"Temperature: {float(_TEMPERATURE)} °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]


def test_check_hp_hh3c_ext_states() -> None:
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(check_hp_hh3c_ext_states(_ITEM, {}, section)) == [
        Result(state=State.OK, summary="Administrative: locked"),
        Result(state=State.OK, summary="Operational: enabled"),
    ]


def test_check_hp_hh3c_ext_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hp_hh3c_ext, "get_value_store", dict)
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(check_hp_hh3c_ext_cpu(_ITEM, {}, section)) == [
        Result(state=State.OK, summary="Total CPU: 8.00%"),
        Metric("util", 8.0, boundaries=(0, None)),
    ]


def test_check_hp_hh3c_ext_mem() -> None:
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert list(check_hp_hh3c_ext_mem(_ITEM, {"levels": (80.0, 90.0)}, section)) == [
        Result(state=State.OK, summary="Usage: 39.00% - 399 MiB of 1.00 GiB"),
        Metric(
            "memused",
            0.39 * _MEM_TOTAL,
            levels=(0.8 * _MEM_TOTAL, 0.9 * _MEM_TOTAL),
            boundaries=(0, _MEM_TOTAL),
        ),
    ]


def test_check_hp_hh3c_ext_cpu_vanished_item(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hp_hh3c_ext, "get_value_store", dict)
    section = parse_hp_hh3c_ext(_STRING_TABLE)
    assert not list(check_hp_hh3c_ext_cpu("MODULE LEVEL3 512", {}, section))


def test_discover_hp_hh3c_ext_invalid_temperature() -> None:
    section = parse_hp_hh3c_ext(
        [
            [["192", "2", "3", "8", "39", _INVALID_TEMPERATURE, str(_MEM_TOTAL)]],
            [["192", "MODULE LEVEL1"]],
        ]
    )
    assert not list(discover_hp_hh3c_ext(section))
    assert list(discover_hp_hh3c_ext_cpu(section)) == [Service(item=_ITEM)]


def test_discover_hp_hh3c_ext_without_temperature() -> None:
    section = parse_hp_hh3c_ext(
        [
            [["192", "2", "3", "8", "39", "", str(_MEM_TOTAL)]],
            [["192", "MODULE LEVEL1"]],
        ]
    )
    assert not list(discover_hp_hh3c_ext(section))
    assert list(discover_hp_hh3c_ext_cpu(section)) == [Service(item=_ITEM)]
    assert list(discover_hp_hh3c_ext_mem(section)) == [Service(item=_ITEM)]


def test_discover_hp_hh3c_ext_cpu_without_mem_size() -> None:
    section = parse_hp_hh3c_ext(
        [
            [["192", "2", "3", "8", "39", str(_TEMPERATURE), ""]],
            [["192", "MODULE LEVEL1"]],
        ]
    )
    assert not list(discover_hp_hh3c_ext_cpu(section))
