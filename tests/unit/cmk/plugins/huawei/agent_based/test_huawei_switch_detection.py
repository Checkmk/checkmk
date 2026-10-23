#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Protocol

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import SNMPDetectSpecification
from cmk.plugins.huawei.agent_based import (
    huawei_switch_cpu,
    huawei_switch_fan,
    huawei_switch_mem,
    huawei_switch_psu,
    huawei_switch_stack,
    huawei_switch_temp,
)


class _Section(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def parsed_section_name(self) -> str | None: ...

    @property
    def detect(self) -> SNMPDetectSpecification: ...


_SECTION_PAIRS: list[tuple[_Section, _Section]] = [
    (
        huawei_switch_cpu.snmp_section_huawei_switch_cpu,
        huawei_switch_cpu.snmp_section_huawei_switch_cpu_huarong,
    ),
    (
        huawei_switch_fan.snmp_section_huawei_switch_fan,
        huawei_switch_fan.snmp_section_huawei_switch_fan_huarong,
    ),
    (
        huawei_switch_mem.snmp_section_huawei_switch_mem,
        huawei_switch_mem.snmp_section_huawei_switch_mem_huarong,
    ),
    (
        huawei_switch_psu.snmp_section_huawei_switch_psu,
        huawei_switch_psu.snmp_section_huawei_switch_psu_huarong,
    ),
    (
        huawei_switch_stack.snmp_section_huawei_switch_stack,
        huawei_switch_stack.snmp_section_huawei_switch_stack_huarong,
    ),
    (
        huawei_switch_temp.snmp_section_huawei_switch_temp,
        huawei_switch_temp.snmp_section_huawei_switch_temp_huarong,
    ),
]


def _detected(sections: tuple[_Section, ...], sys_object_id: str) -> list[_Section]:
    return [
        section
        for section in sections
        if evaluate_snmp_detection(
            detect_spec=section.detect,
            oid_value_getter={".1.3.6.1.2.1.1.2.0": sys_object_id}.get,
        )
    ]


@pytest.mark.parametrize(
    "huawei_section, huarong_section",
    [pytest.param(*pair, id=pair[0].name) for pair in _SECTION_PAIRS],
)
@pytest.mark.parametrize(
    "sys_object_id, expected_index",
    [
        pytest.param(".1.3.6.1.4.1.2011.2.23.1.2", 0, id="huawei enterprise number"),
        pytest.param(".1.3.6.1.4.1.56813.2.23.1.2", 1, id="huarong enterprise number"),
    ],
)
def test_exactly_one_variant_is_detected(
    huawei_section: _Section,
    huarong_section: _Section,
    sys_object_id: str,
    expected_index: int,
) -> None:
    pair = (huawei_section, huarong_section)
    assert _detected(pair, sys_object_id) == [pair[expected_index]]


@pytest.mark.parametrize(
    "huawei_section, huarong_section",
    [pytest.param(*pair, id=pair[0].name) for pair in _SECTION_PAIRS],
)
def test_other_vendor_is_not_detected(
    huawei_section: _Section,
    huarong_section: _Section,
) -> None:
    assert not _detected((huawei_section, huarong_section), ".1.3.6.1.4.1.9.1.1745")


@pytest.mark.parametrize(
    "huawei_section, huarong_section",
    [pytest.param(*pair, id=pair[0].name) for pair in _SECTION_PAIRS],
)
def test_huarong_section_feeds_huawei_plugin(
    huawei_section: _Section,
    huarong_section: _Section,
) -> None:
    assert huarong_section.parsed_section_name == huawei_section.name
