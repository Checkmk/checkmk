#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
                [
                    "Waterflow",
                    "0.0 l/min",
                    "130.0 l/min",
                    "0.0 l/min",
                    "OK",
                    "2",
                    "Control-Valve",
                    "32 %",
                    "OK",
                    "2",
                    "Cooling-Capacity",
                    "0 W",
                    "OK",
                ],
            ],
            ["Waterflow", "0.0 l/min", "130.0 l/min", "0.0 l/min", "OK"],
            id="Waterflow measurements are parsed correctly",
        ),
        pytest.param(
            [
                [
                    "Control-Valve",
                    "32 %",
                    "OK",
                    "2",
                    "Cooling-Capacity",
                    "0 W",
                    "OK",
                ],
            ],
            [],
            id="Waterflow measurements are parsed correctly",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_cmciii_lcp_waterflow(string_table: StringTable, section: StringTable):
    check = Check("cmciii_lcp_waterflow")
    assert list(check.run_parse(string_table)) == section


@pytest.mark.parametrize(
    "string_table, discovered_item",
    [
        pytest.param(
            ["Waterflow", "0.0 l/min", "130.0 l/min", "0.0 l/min", "OK"],
            [(None, {})],
            id="Waterflow sensor is discovered within OID range.",
        ),
        pytest.param(
            [],
            [],
            id="Waterflow sensor is not discovered when there are no measurements for it.",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_cmciii_lcp_waterflow(string_table: StringTable, discovered_item):
    check = Check("cmciii_lcp_waterflow")
    assert list(check.run_discovery(string_table)) == discovered_item


@pytest.mark.parametrize(
    "string_table, check_results",
    [
        pytest.param(
            ["Waterflow", "0.0 l/min", "130.0 l/min", "0.0 l/min", "OK"],
            [
                0,
                "Waterflow Status: OK Flow: 0.0, MinFlow: 0.0, MaxFLow: 130.0",
                [("flow", "0.0l/min", "0.0:130.0", 0, 0)],
            ],
            id="Check results of waterflow sensor measurements",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_cmciii_lcp_waterflow(string_table: StringTable, check_results: Sequence):
    check = Check("cmciii_lcp_waterflow")
    assert list(check.run_check(None, {}, string_table)) == check_results


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_cmciii_lcp_waterflow_empty_section():
    check = Check("cmciii_lcp_waterflow")
    assert check.run_check(None, {}, []) is None
