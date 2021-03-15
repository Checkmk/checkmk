#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [
    ([["1", "1", "2"], ["2", "0", "2"]], [("1", "ups_out_load_default_levels")]),
])
def test_ups_out_load_discovery(info, expected_result):
    result = Check("ups_out_load").run_discovery(info)
    assert result == expected_result


@pytest.mark.parametrize("item, params, info, expected_result", [
    ("1", (85, 90), [["1", "1", "2"]],
     (0, "load: 2 (warn/crit at 85/90) ", [("out_load", 2, 85, 90, 100)])),
    ("1", (85, 90), [["1", "1", "89"]],
     (1, "load: 89 (warn/crit at 85/90) ", [("out_load", 89, 85, 90, 100)])),
    ("1", (85, 90), [["1", "1", "99"]],
     (2, "load: 99 (warn/crit at 85/90) ", [("out_load", 99, 85, 90, 100)])),
    ("3", (85, 90), [["1", "1", "99"]], (3, "Phase 3 not found in SNMP output")),
])
def test_ups_out_load_check(item, params, info, expected_result):
    result = Check("ups_out_load").run_check(item, params, info)
    assert result == expected_result
