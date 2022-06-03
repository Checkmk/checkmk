#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.sentry_pdu_outlets import (
    check_sentry_pdu_outlets,
    check_sentry_pdu_outlets_v4,
    discovery_sentry_pdu_outlets,
    parse_sentry_pdu_outlets,
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            [["A1", "A_Outlet1", "0"], ["A2", "A_Outlet2", "3"]],
            {"A1 A_1": 0, "A2 A_2": 3},
            id="sentry_pdu_outlets",
        )
    ],
)
def test_parse_sentry_pdu_outlets(string_table, expected_section):
    section = parse_sentry_pdu_outlets(string_table)
    assert section == expected_section


@pytest.mark.parametrize(
    "parsed, expected_discovery",
    [
        pytest.param(
            {"A1 A_1": 0, "A2 A_2": 3},
            [Service(item="A1 A_1"), Service(item="A2 A_2")],
            id="sentry_pdu_outlets",
        )
    ],
)
def test_inventory_sentry_pdu_outlets(
    parsed: Mapping[str, int],
    expected_discovery: Sequence[Service],
) -> None:
    result = list(discovery_sentry_pdu_outlets(parsed))
    assert result == expected_discovery


@pytest.mark.parametrize(
    "parsed, item, expected_result",
    [
        pytest.param(
            {"A1 A_1": 0, "A2 A_2": 3},
            "A1 A_1",
            [Result(state=State.OK, summary="Status: off")],
            id="known_state",
        ),
        pytest.param(
            {"A1 A_1": 0, "A2 A_2": 33},
            "A2 A_2",
            [Result(state=State.UNKNOWN, summary="Unhandled state: 33")],
            id="unknown_state",
        ),
    ],
)
def test_check_sentry_pdu_outlets(
    parsed: Mapping[str, int],
    item: str,
    expected_result: Sequence[Result],
) -> None:
    result = list(check_sentry_pdu_outlets(item, parsed))
    assert result == expected_result


@pytest.mark.parametrize(
    "parsed, item, expected_result",
    [
        pytest.param(
            {"A1 A_1": 14, "A2 A_2": 3},
            "A1 A_1",
            [Result(state=State.CRIT, summary="Status: low alarm")],
            id="known_state_v4",
        ),
        pytest.param(
            {"A1 A_1": 14, "A2 A_2": 3},
            "A3 A_3",
            [],
            id="missing_item",
        ),
    ],
)
def test_check_sentry_pdu_outlets_v4(
    parsed: Mapping[str, int],
    item: str,
    expected_result: Sequence[Result],
) -> None:
    result = list(check_sentry_pdu_outlets_v4(item, parsed))
    assert result == expected_result
