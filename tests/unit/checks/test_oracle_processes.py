#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Union

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "section, discovered_item",
    [
        pytest.param(
            [["DB1DEV2", "1152", "1500"]],
            [Service(item="DB1DEV2")],
            id="One valid Oracle process is discovered",
        ),
        pytest.param(
            [["Error", "Message:"]],
            [Service(item="Error")],
            id="One error Oracle process is discovered",
        ),
        pytest.param(
            [],
            [],
            id="Empty section leads to no processes being discovered",
        ),
    ],
)
def test_discover_oracle_processes(
    section: StringTable,
    discovered_item: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("oracle_processes")]
    assert list(check.discovery_function(section)) == discovered_item


@pytest.mark.parametrize(
    "section, item, check_result",
    [
        pytest.param(
            [["FDMTST", "50", "300"]],
            "FDMTST",
            [
                Result(
                    state=State.OK,
                    summary="50 of 300 processes are used (16%, warn/crit at 70%/90%)",
                ),
                Metric(name="processes", value=50, levels=(210.0, 270.0)),
            ],
            id="Oracle process OK state",
        ),
        pytest.param(
            [["DB1DEV2", "1152", "1500"]],
            "DB1DEV2",
            [
                Result(
                    state=State.WARN,
                    summary="1152 of 1500 processes are used (76%, warn/crit at 70%/90%)",
                ),
                Metric(name="processes", value=1152, levels=(1050.0, 1350.0)),
            ],
            id="Oracle process state WARN",
        ),
        pytest.param(
            [["DB1DEV2", "1450", "1500"]],
            "DB1DEV2",
            [
                Result(
                    state=State.CRIT,
                    summary="1450 of 1500 processes are used (96%, warn/crit at 70%/90%)",
                ),
                Metric(name="processes", value=1450, levels=(1050.0, 1350.0)),
            ],
            id="Oracle process state CRIT",
        ),
        pytest.param(
            [["Error", "Message:"], ["Error", "Message:"]],
            "Error",
            [
                Result(
                    state=State.UNKNOWN,
                    summary='Found error in agent output "Message:"',
                )
            ],
            id="UNKNOWN on error from 1.6 solaris agent plugin output",
        ),
    ],
)
def test_check_oracle_processes(
    section: StringTable,
    item: str,
    check_result: Sequence[Union[Result, Metric]],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("oracle_processes")]
    assert (
        list(check.check_function(item=item, params={"levels": (70.0, 90.0)}, section=section))
        == check_result
    )
