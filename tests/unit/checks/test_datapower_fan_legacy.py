#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple
import pytest
from testlib import Check

from cmk.base.plugins.agent_based.datapower_fan import Fan

_SECTION = {
    "Tray 1 Fan 1": Fan(
        state="4",
        state_txt="operating normally",
        speed="9700",
    ),
    "Tray 1 Fan 2": Fan(
        state="5",
        state_txt="reached upper non-critical limit",
        speed="5600",
    ),
    "Tray 1 Fan 3": Fan(
        state="7",
        state_txt="reached upper non-recoverable limit",
        speed="9800",
    ),
    "Tray 1 Fan 4": Fan(
        state="10",
        state_txt="Invalid",
        speed="5400",
    ),
}


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_datapower_fan() -> None:
    assert list(Check("datapower_fan").run_discovery(_SECTION)) == [
        ("Tray 1 Fan 1", None),
        ("Tray 1 Fan 2", None),
        ("Tray 1 Fan 3", None),
        ("Tray 1 Fan 4", None),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "Tray 1 Fan 1",
            (0, "operating normally, 9700 rpm"),
            id="normal",
        ),
        pytest.param(
            "Tray 1 Fan 3",
            (2, "reached upper non-recoverable limit, 9800 rpm"),
            id="upper non-critical limit",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_datapower_fan(
    item: str,
    expected_result: Tuple[int, str],
) -> None:
    assert (Check("datapower_fan").run_check(
        item,
        None,
        _SECTION,
    ) == expected_result)
