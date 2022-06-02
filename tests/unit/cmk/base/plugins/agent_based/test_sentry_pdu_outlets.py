#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.sentry_pdu_outlets import parse_sentry_pdu_outlets


@pytest.mark.parametrize(
    "string_table, expected_section",
    [([["A1", "A_Outlet1", "0"], ["A2", "A_Outlet2", "3"]], {"A1 A_1": 0, "A2 A_2": 3})],
)
def test_parse_sentry_pdu_outlets(string_table, expected_section):
    section = parse_sentry_pdu_outlets(string_table)
    assert section == expected_section


@pytest.mark.parametrize(
    "parsed, expected_discovery",
    [({"A1 A_1": 0, "A2 A_2": 3}, [Service(item="A1 A_1"), Service(item="A2 A_2")])],
)
def test_inventory_sentry_pdu_outlets(
    fix_register: FixRegister,
    parsed: Mapping[str, int],
    expected_discovery: Sequence[DiscoveryResult],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("sentry_pdu_outlets")]
    result = list(check_plugin.discovery_function(parsed))
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
    fix_register: FixRegister,
    parsed: Mapping[str, int],
    item: str,
    expected_result: Sequence[CheckResult],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("sentry_pdu_outlets")]
    result = list(check_plugin.check_function(item=item, params={}, section=parsed))
    assert result == expected_result
