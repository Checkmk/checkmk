#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture(name="check")
def _3par_system_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("3par_system")]


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            [
                [
                    '{"id":168676,"name":"test-name","systemVersion":"9.5.3.12","IPv4Addr":"172.17.37.20","model":"HPEAlletra9060","serialNumber":"CZ222908M6","totalNodes":2,"masterNode":0}'
                ]
            ],
            [
                Result(
                    state=State.OK,
                    summary="Model: HPEAlletra9060, Version: 9.5.3.12, Serial number: CZ222908M6, Online nodes: 0/0",
                ),
            ],
            id="No online and cluster nodes available",
        ),
    ],
)
def test_check_3par_system(
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    parse_3par_system = fix_register.agent_sections[SectionName("3par_system")].parse_function
    assert (
        list(
            check.check_function(
                item="",
                params={},
                section=parse_3par_system(section),
            )
        )
        == expected_check_result
    )
