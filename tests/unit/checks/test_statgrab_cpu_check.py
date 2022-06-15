#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import (
    assertCheckResultsEqual,
    assertMKCounterWrapped,
    CheckResult,
    mock_item_state,
)

pytestmark = pytest.mark.checks

info_statgrab_cpu_hpux = [
    ["idle", "300"],
    ["iowait", "300"],
    ["kernel", "300"],
    ["nice", "300"],
    ["swap", "0"],
    ["systime", "300"],
    ["total", "1800"],
    ["user", "300"],
]

# If mock_state is a tuple, it is returned upon
# every call to `get_item_state`. Let's say
# The check ran 23 seconds ago, and all values
# were zero:
mock_state_tuple = (23.0, 0)

# If mock_state is a dictionary, the values will
# be returned according to their key,
# as you would expect.
mock_state_dict = {
    "cpu.util.1": (3, 200),  # user
    "cpu.util.2": (1, 220),  # nice
    "cpu.util.3": (4, 100),  # system
    "cpu.util.4": (1, 123),  # idle
    "cpu.util.5": (5, 50),  # iowait
    "cpu.util.6": (9, 0),  # irq
    "cpu.util.7": (2, 0),  # softirq
    "cpu.util.8": (6, 0),  # steal
    "cpu.util.9": (5, 0),  # guest
    "cpu.util.10": (3, 0),  # guest_nice
}


# If mock_state is a function, it must accept two
# arguments, just like dict.get:
def mock_state_function(key, _default):
    counter = int(key.split(".")[-1])
    return (23, (counter < 6) * 300)


expected_result_1 = CheckResult(
    [
        (0, "User: 40.00%", [("user", 40.0, None, None, None, None)]),
        (0, "System: 20.00%", [("system", 20.0, None, None, None, None)]),
        (0, "Wait: 20.00%", [("wait", 20.0, None, None, None, None)]),
        (0, "Total CPU: 80.00%", [("util", 80.0, None, None, 0, None)]),
    ]
)

expected_result_2 = CheckResult(
    [
        (0, "User: 22.30%", [("user", 22.304832713754646, None, None, None, None)]),
        (0, "System: 24.78%", [("system", 24.783147459727385, None, None, None, None)]),
        (0, "Wait: 30.98%", [("wait", 30.97893432465923, None, None, None, None)]),
        (0, "Total CPU: 78.07%", [("util", 78.06691449814126, None, None, 0, None)]),
    ]
)


@pytest.mark.parametrize(
    "info,mockstate,expected_result",
    [
        (info_statgrab_cpu_hpux, mock_state_tuple, expected_result_1),
        (info_statgrab_cpu_hpux, mock_state_dict, expected_result_2),
    ],
)
def test_statgrab_cpu_check(info, mockstate, expected_result) -> None:

    check = Check("statgrab_cpu")

    # set up mocking of `get_item_state`
    with mock_item_state(mockstate):
        result = CheckResult(check.run_check(None, {}, info))
    assertCheckResultsEqual(result, expected_result)


@pytest.mark.parametrize(
    "info,mockstate",
    [
        (info_statgrab_cpu_hpux, mock_state_function),
    ],
)
def test_statgrab_cpu_check_error(info, mockstate) -> None:

    check = Check("statgrab_cpu")

    with mock_item_state(mockstate):
        # the mock values are designed to raise an exception.
        # to make sure it is raised, use this:
        with assertMKCounterWrapped("Too short time difference since last check"):
            CheckResult(check.run_check(None, {}, info))
        # # You could omit the error message it you don't care about it:
        # with assertMKCounterWrapped()
        #     CheckResult(check.run_check(None, {}, info))
