#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping

import pytest

from cmk.utils.sectionname import SectionName

# pylint: disable=cmk-module-layer-violation
from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection

from cmk.base.api.agent_based.register import AgentBasedPlugins
from cmk.base.legacy_checks.hp_hh3c_ext import parse_hp_hh3c_ext

_SYS_OBJECT_ID = ".1.3.6.1.2.1.1.2.0"
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
            {_SYS_OBJECT_ID: ".1.3.6.1.4.1.25506.11.1.290", _STATE_ENTRY_OID: "0"},
            id="HPE 5710 24XGT 6QS+/2QS28",
        ),
        pytest.param(
            {_SYS_OBJECT_ID: ".1.3.6.1.4.1.25506.11.1.239", _STATE_ENTRY_OID: "0"},
            id="formerly allow-listed .239",
        ),
        pytest.param(
            {_SYS_OBJECT_ID: ".1.3.6.1.4.1.25506.11.1.87", _STATE_ENTRY_OID: "0"},
            id="formerly allow-listed .87",
        ),
    ],
)
def test_hp_hh3c_ext_snmp_detection(
    agent_based_plugins: AgentBasedPlugins, oid_data: Mapping[str, str]
) -> None:
    section = agent_based_plugins.snmp_sections[SectionName("hp_hh3c_ext")]
    assert (
        evaluate_snmp_detection(
            detect_spec=section.detect_spec,
            oid_value_getter=oid_data.get,
        )
        is True
    )


@pytest.mark.parametrize(
    "oid_data",
    [
        pytest.param(
            {_SYS_OBJECT_ID: ".1.3.6.1.4.1.25506.11.1.290"},
            id="H3C device without HH3C-ENTITY-EXT MIB",
        ),
        pytest.param(
            {_SYS_OBJECT_ID: ".1.3.6.1.4.1.9.1.1745", _STATE_ENTRY_OID: "0"},
            id="other vendor",
        ),
    ],
)
def test_hp_hh3c_ext_snmp_detection_negative(
    agent_based_plugins: AgentBasedPlugins, oid_data: Mapping[str, str]
) -> None:
    section = agent_based_plugins.snmp_sections[SectionName("hp_hh3c_ext")]
    assert (
        evaluate_snmp_detection(
            detect_spec=section.detect_spec,
            oid_value_getter=oid_data.get,
        )
        is False
    )


def test_parse_hp_hh3c_ext() -> None:
    parsed = parse_hp_hh3c_ext(_STRING_TABLE)
    assert parsed[_ITEM] == {
        "temp": _TEMPERATURE,
        "cpu": 8,
        "mem_total": _MEM_TOTAL,
        "mem_used": 0.39 * _MEM_TOTAL,
        "admin": "2",
        "oper": "3",
    }


def test_parse_hp_hh3c_ext_without_mem_size() -> None:
    parsed = parse_hp_hh3c_ext(
        [
            [["192", "2", "3", "8", "39", str(_TEMPERATURE), ""]],
            [["192", "MODULE LEVEL1"]],
        ]
    )
    assert parsed[_ITEM]["mem_total"] == 0
    assert parsed[_ITEM]["mem_used"] == 0


def test_parse_hp_hh3c_ext_without_temperature() -> None:
    parsed = parse_hp_hh3c_ext(
        [
            [["192", "2", "3", "8", "39", "", str(_MEM_TOTAL)]],
            [["192", "MODULE LEVEL1"]],
        ]
    )
    assert parsed[_ITEM]["temp"] == int(_INVALID_TEMPERATURE)
    assert parsed[_ITEM]["cpu"] == 8
