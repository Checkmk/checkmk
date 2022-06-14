#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks

range_data = {
    "total": 20,
    "ranges": collections.OrderedDict(
        [
            ("0.1", ("0-0.1 ms", 0)),
            ("0.2", ("0.1-0.2 ms", 0)),
            ("0.5", ("0.2-0.5 ms", 2)),
            ("1", ("0.5-1.0 ms", 1)),
            ("2", ("1-2 ms", 1)),
            ("5", ("2-5 ms", 1)),
            ("10", ("5-10 ms", 10)),
            ("20", ("10-20 ms", 1)),
            ("50", ("20-50 ms", 1)),
            ("100", ("50-100 ms", 1)),
            ("200", ("100-200 ms", 1)),
            ("500", ("200-500 ms", 1)),
            ("1000", ("500+ ms", 0)),
        ]
    ),
}


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            {
                "range_reference": "0.1",
                "read": (99, 100),
            },
            {
                "itemxyz": {"read": range_data},
            },
            (2, "At or above 0-0.1 ms: 100% (warn/crit at 99.0%/100%)", []),
        ),
        (
            {
                "range_reference": "50",
                "read": (99, 100),
            },
            {
                "itemxyz": {"read": range_data},
            },
            (0, "At or above 20-50 ms: 20.0%", []),
        ),
        (
            {
                "range_reference": "1000",
                "read": (99, 100),
            },
            {
                "itemxyz": {"read": range_data},
            },
            (0, "At or above 500+ ms: 0%", []),
        ),
    ],
)
def test_nimble_latency_ranges(params, data, result) -> None:
    """The user can specify a parameter range_reference, which serves as a starting
    point from which values should start to be stacked and checked against levels.
    Test whether the stacking is correct."""

    check = Check("nimble_latency")
    actual_results = list(check.run_check("itemxyz", params, data))
    assert result == actual_results[0]


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            {
                "range_reference": "50",
                "read": (30, 40),
                "write": (1, 2),
            },
            {
                "itemxyz": {"read": range_data},
            },
            (0, "At or above 20-50 ms: 20.0%", []),
        ),
    ],
)
def test_nimble_latency_read_params(params, data, result) -> None:
    """Test that latency read levels are applied to read types only."""

    read_check = Check("nimble_latency")
    write_check = Check("nimble_latency.write")
    read_results = list(read_check.run_check("itemxyz", params, data))
    write_results = list(write_check.run_check("itemxyz", params, data))
    assert result == read_results[0]
    assert not write_results


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            {
                "range_reference": "50",
                "read": (30, 40),
                "write": (1, 2),
            },
            {
                "itemxyz": {"write": range_data},
            },
            (2, "At or above 20-50 ms: 20.0% (warn/crit at 1.0%/2.0%)", []),
        ),
    ],
)
def test_nimble_latency_write_params(params, data, result) -> None:
    """Test that latency write levels are applied to write types only."""

    read_check = Check("nimble_latency")
    write_check = Check("nimble_latency.write")
    read_results = list(read_check.run_check("itemxyz", params, data))
    write_results = list(write_check.run_check("itemxyz", params, data))
    assert result == write_results[0]
    assert not read_results
