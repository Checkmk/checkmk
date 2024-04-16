#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from tests.unit.conftest import FixRegister

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

from cmk.agent_based.v1 import get_value_store

_STRING_TABLE = [
    ["msg", "2000000000"],
    ["rollovers", "2000000000"],
    ["regular", "2000000000"],
    ["warning", "2000000000"],
    ["user", "2000000000"],
]


@pytest.fixture(name="check_plugin", scope="module")
def check_plugin_fixutre(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("mongodb_asserts")]


@pytest.fixture(name="section_mongodb_asserts", scope="module")
def section_fixture(fix_register: FixRegister) -> Mapping[str, Any]:
    return fix_register.agent_sections[SectionName("mongodb_asserts")].parse_function(_STRING_TABLE)


def test_discover_mongodb_asserts(
    check_plugin: CheckPlugin,
    section_mongodb_asserts: Mapping[str, Any],
) -> None:
    assert list(check_plugin.discovery_function(section_mongodb_asserts)) == [Service()]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "",
            {},
            [
                Result(state=State.OK, summary="1.21 Msg Asserts/sec"),
                Metric("assert_msg", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 Rollovers Asserts/sec"),
                Metric("assert_rollovers", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 Regular Asserts/sec"),
                Metric("assert_regular", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 Warning Asserts/sec"),
                Metric("assert_warning", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 User Asserts/sec"),
                Metric("assert_user", 1.2051717419264805),
            ],
            id="All OK",
        ),
        pytest.param(
            "",
            {"msg_assert_rate": (1.0, 2.0), "warning_assert_rate": (0.5, 1.0)},
            [
                Result(state=State.WARN, summary="1.21 Msg Asserts/sec"),
                Metric("assert_msg", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 Rollovers Asserts/sec"),
                Metric("assert_rollovers", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 Regular Asserts/sec"),
                Metric("assert_regular", 1.2051717419264805),
                Result(state=State.CRIT, summary="1.21 Warning Asserts/sec"),
                Metric("assert_warning", 1.2051717419264805),
                Result(state=State.OK, summary="1.21 User Asserts/sec"),
                Metric("assert_user", 1.2051717419264805),
            ],
            id="One WARN one CRIT",
        ),
    ],
)
def test_check_mongodb_asserts(
    check_plugin: CheckPlugin,
    section_mongodb_asserts: Mapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    get_value_store().update(
        {
            "msg": (0, 0),
            "rollovers": (0, 0),
            "regular": (0, 0),
            "warning": (0, 0),
            "user": (0, 0),
        }
    )
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("UTC"))):
        assert (
            list(
                check_plugin.check_function(
                    item=item,
                    params=params,
                    section=section_mongodb_asserts,
                )
            )
            == expected_result
        )
