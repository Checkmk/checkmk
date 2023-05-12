#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.checkers.checking import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "Error Message:          MyDatabase",
            [
                [
                    "Error Message:          MyDatabase",
                    "FAILURE",
                    "ERROR: ORA-123456: Some kind of error occurred",
                ]
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Error Message:          MyDatabase, FAILURE, ERROR: ORA-123456: Some kind of error occurred",
                )
            ],
        )
    ],
)
def test_check_oracle_recovery_status(
    fix_register: FixRegister,
    item: str,
    info: list[list[str]],
    expected_result: Sequence[tuple[str, Mapping]],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_recovery_status")]
    result = list(check_plugin.check_function(item=item, params={}, section=info))
    assert result == expected_result
