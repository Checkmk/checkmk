#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.enviromux_remote_input import (
    check_enviromux_remote_input,
    discover_enviromux_remote_input,
    InputStatus,
    InputValue,
    parse_enviromux_remote_input,
    RemoteInput,
    Section,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                ["136", "Description A", "1", "1", "0"],
                ["101", "Description B", "0", "3", "0"],
            ],
            {
                "Description B 101": RemoteInput(
                    value=InputValue.closed,
                    status=InputStatus.alert,
                    normal_value=InputValue.closed,
                ),
                "Description A 136": RemoteInput(
                    value=InputValue.open,
                    status=InputStatus.normal,
                    normal_value=InputValue.closed,
                ),
            },
            id="remote_inputs",
        )
    ],
)
def test_parse_enviromux_remote_input(string_table: StringTable, expected_result: Section) -> None:
    result = parse_enviromux_remote_input(string_table)
    assert result == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            {
                "Description B 101": RemoteInput(
                    value=InputValue.closed,
                    status=InputStatus.alert,
                    normal_value=InputValue.closed,
                ),
                "Description A 136": RemoteInput(
                    value=InputValue.open,
                    status=InputStatus.notconnected,
                    normal_value=InputValue.closed,
                ),
                "Description C 166": RemoteInput(
                    value=InputValue.open,
                    status=InputStatus.normal,
                    normal_value=InputValue.closed,
                ),
            },
            [Service(item="Description B 101"), Service(item="Description C 166")],
            id="remote_inputs",
        )
    ],
)
def test_discover_enviromux_remote_input(
    section: Section, expected_result: DiscoveryResult
) -> None:
    result = list(discover_enviromux_remote_input(section))
    assert result == expected_result


@pytest.mark.parametrize(
    "item, section, expected_result",
    [
        pytest.param(
            "Description B 101",
            {
                "Description B 101": RemoteInput(
                    value=InputValue.closed,
                    status=InputStatus.alert,
                    normal_value=InputValue.closed,
                )
            },
            [
                Result(state=State.OK, summary="Input value: closed, Normal value: closed"),
                Result(state=State.CRIT, summary="Input status: alert"),
            ],
            id="crit_status",
        ),
        pytest.param(
            "Description A 136",
            {
                "Description A 136": RemoteInput(
                    value=InputValue.open,
                    status=InputStatus.dismissed,
                    normal_value=InputValue.closed,
                ),
            },
            [
                Result(state=State.OK, summary="Input value: open, Normal value: closed"),
                Result(state=State.CRIT, summary="Input value different from normal"),
                Result(state=State.WARN, summary="Input status: dismissed"),
            ],
            id="invalid_value",
        ),
        pytest.param(
            "Description B 101",
            {
                "Description A 136": RemoteInput(
                    value=InputValue.open,
                    status=InputStatus.dismissed,
                    normal_value=InputValue.closed,
                ),
            },
            [],
            id="missing_item",
        ),
    ],
)
def test_check_enviromux_remote_input(
    item: str, section: Section, expected_result: CheckResult
) -> None:
    result = list(check_enviromux_remote_input(item, section))
    assert result == expected_result


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        pytest.param(
            [
                ["136", "Description A", "1", "4", "0"],
            ],
            "Description A 136",
            [
                Result(state=State.OK, summary="Input value: open, Normal value: closed"),
                Result(state=State.CRIT, summary="Input value different from normal"),
                Result(state=State.WARN, summary="Input status: acknowledged"),
            ],
            id="different_values",
        ),
        pytest.param(
            [
                ["100", "Description B", "1", "1", "1"],
            ],
            "Description B 100",
            [
                Result(state=State.OK, summary="Input value: open, Normal value: open"),
                Result(state=State.OK, summary="Input status: normal"),
            ],
            id="normal_state",
        ),
    ],
)
def test_enviromux_remote_input(
    string_table: StringTable, item: str, expected_result: CheckResult
) -> None:
    section = parse_enviromux_remote_input(string_table)

    service = list(discover_enviromux_remote_input(section))
    assert len(service) == 1
    assert service[0].item == item

    check_result = list(check_enviromux_remote_input(item, section))
    assert check_result == expected_result
