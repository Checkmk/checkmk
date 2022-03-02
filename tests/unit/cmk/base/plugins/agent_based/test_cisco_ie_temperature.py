#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import pytest

from cmk.base.plugins.agent_based import cisco_ie_temp
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable
from cmk.base.plugins.agent_based.cisco_ie_temp import Section, SensorId
from cmk.base.plugins.agent_based.utils.temperature import TempParamDict

OK = 25
WARN = 30
CRIT = 35


@pytest.fixture(name="sensors_count")
def fixture_sensors_count() -> int:
    return 1


@pytest.fixture(name="sensor_id")
def fixture_sensor_id(sensors_count: int) -> str:
    return "1" if sensors_count == 1 else "{}"


@pytest.fixture(name="temperature")
def fixture_temperature() -> int:
    return OK


@pytest.fixture(name="string_table_element")
def fixture_string_table_element(sensor_id: str, temperature: int) -> List[str]:
    return [sensor_id, str(temperature)]


@pytest.fixture(name="string_table")
def fixture_string_table(string_table_element: List[str]) -> StringTable:
    return [string_table_element]


@pytest.fixture(name="section")
def fixture_section(string_table: StringTable) -> cisco_ie_temp.Section:
    return cisco_ie_temp.parse(string_table)


@pytest.fixture(name="warn_level")
def fixture_warn_level() -> int:
    return WARN


@pytest.fixture(name="crit_level")
def fixture_crit_level() -> int:
    return CRIT


@pytest.fixture(name="params")
def fixture_params(warn_level: int, crit_level: int) -> TempParamDict:
    return {"levels": (warn_level, crit_level)}


@pytest.fixture(name="check_result")
def fixture_check_result(sensor_id: str, params: TempParamDict, section: Section) -> CheckResult:
    return cisco_ie_temp.check(SensorId(sensor_id), params, section)


def test_parse(string_table: StringTable):
    section = cisco_ie_temp.parse(string_table)
    assert section is not None


def test_discovery(sensors_count: int, section: Section):
    assert len(list(cisco_ie_temp.discover(section))) == sensors_count


def test_check_result_includes_metric(check_result: CheckResult):
    assert any(isinstance(m, Metric) for m in check_result)


def test_check_with_no_matching_sensor_id(sensor_id: str, section: Section):
    check_result = list(cisco_ie_temp.check(SensorId(f"invalid_{sensor_id}"), {}, section))
    assert len(check_result) == 0
