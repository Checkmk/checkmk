#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[attr-defined]
from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_amperage

# mypy can not handle globals ignore in dell_poweredge https://github.com/python/mypy/issues/9318


def test_check_dell_poweredge_amperage_state_simple() -> None:
    result = check_dell_poweredge_amperage(
        "My-test-item",
        None,
        # actual snmp data
        [["1", "3", "2", "3", "168", "26", "My-test-item", "980", "896"]],
    )
    assert result == (
        0,
        "168 Watt  (upper limits 896/980)",
        [("power", "168W", "896", "980", "", 1078.0)],
    )


def test_check_dell_poweredge_amperage_state_unknown() -> None:
    result = check_dell_poweredge_amperage(
        "My-test-item",
        None,
        # as seen in the crash report:
        [["1", "1", "1", "2", "", "23", "My-test-item", "", ""]],
    )
    assert result[0] == 3
    assert "unknown" in result[1].lower()
