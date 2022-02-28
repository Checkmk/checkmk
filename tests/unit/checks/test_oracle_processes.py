#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Union

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string_table, discovered_item",
    [
        pytest.param(
            [["DB1DEV2", "1152", "1500"]],
            [("DB1DEV2", {})],
            id="One Oracle process is discovered",
        ),
        pytest.param(
            [],
            [],
            id="Empty section leads to no processes being discovered",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_oracle_processes(
    string_table: StringTable,
    discovered_item: Sequence[str],
) -> None:
    assert list(Check("oracle_processes").run_discovery(string_table)) == discovered_item


@pytest.mark.parametrize(
    "string_table, item, check_results",
    [
        pytest.param(
            [["FDMTST", "50", "300"]],
            "FDMTST",
            [
                0,
                "50 of 300 processes are used (16%, warn/crit at 70%/90%)",
                [("processes", 50, 210.0, 270.0)],
            ],
            id="OK oracle process",
        ),
        pytest.param(
            [["DB1DEV2", "1152", "1500"]],
            "DB1DEV2",
            [
                1,
                "1152 of 1500 processes are used (76%, warn/crit at 70%/90%)",
                [("processes", 1152, 1050.0, 1350.0)],
            ],
            id="WARN oracle process",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_oracle_processes(
    string_table: StringTable,
    item: str,
    check_results: Sequence[Union[Result, Metric]],
) -> None:
    assert (list(Check("oracle_processes").run_check(item, {"levels": (70.0, 90.0)},
                                                     string_table)) == check_results)
