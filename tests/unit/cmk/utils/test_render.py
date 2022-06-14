#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.render


@pytest.mark.parametrize(
    "entry, result",
    [
        ((5,), "5.00 B"),
        ((5, 1000, False), "5 B"),
        ((2300,), "2.25 kB"),
        ((-2300,), "-2.25 kB"),
        ((3e6,), "2.86 MB"),
        ((3e6, 1000, 2, "B"), "3.00 MB"),
        ((4e9,), "3.73 GB"),
        ((-5e12,), "-4.55 TB"),
        ((6e15,), "5.33 PB"),
    ],
)
def test_fmt_bytes(entry, result) -> None:
    assert cmk.utils.render.fmt_bytes(*entry) == result


@pytest.mark.parametrize("args, result", [((0.433 / 1, 10), (4.33, -1)), ((5, 10), (5, 0))])
def test_frexpb(args, result) -> None:
    assert cmk.utils.render._frexpb(*args) == result


@pytest.mark.parametrize(
    "perc, result",
    [
        (0.0, "0%"),
        (9.0e-05, "0.00009%"),
        (0.00009, "0.00009%"),
        (0.00103, "0.001%"),
        (0.0019, "0.002%"),
        (0.129, "0.13%"),
        (8.25752, "8.26%"),
        (8, "8.0%"),
        (80, "80.0%"),
        (100.123, "100%"),
        (200.123, "200%"),
        (1234567, "1234567%"),
    ],
)
def test_percent_std(perc, result) -> None:
    assert cmk.utils.render.percent(perc, False) == result


@pytest.mark.parametrize(
    "value, precision, result",
    [
        (0.00009, 2, "9.00e-5"),
        (0.00009, 1, "9.0e-5"),
        (0.00009, 0, "9e-5"),
        (0.009, 3, "0.009"),
        (0.009, 2, "0.01"),
        (0.009, 1, "0.0"),
        (0.009, 0, "0"),
        (0.1, 2, "0.10"),
        (100, 0, "100"),
        (100, 2, "100"),
        (100, 4, "100.00"),
        (100, 5, "100.000"),
        (10000, 5, "10000.0"),
        (10000, 6, "10000.00"),
        (1000000, 2, "10.00e+5"),
        (9000000, 2, "9.00e+6"),
    ],
)
def test_scientific(value, precision, result) -> None:
    assert cmk.utils.render.scientific(value, precision) == result


@pytest.mark.parametrize(
    "perc, result",
    [
        (0.00009, "9.0e-5%"),
        (0.00019, "0.0002%"),
        (12345, "12345%"),
        (1234567, "1.2e+6%"),
    ],
)
def test_percent_scientific(perc, result) -> None:
    assert cmk.utils.render.percent(perc, True) == result


@pytest.mark.parametrize(
    "value, kwargs, result",
    [
        (10000486, {"precision": 5}, "10.00049 M"),
        (100000000, {"drop_zeroes": False}, "100.00 M"),
    ],
)
def test_fmt_number_with_precision(value, kwargs, result) -> None:
    assert cmk.utils.render.fmt_number_with_precision(value, **kwargs) == result


@pytest.mark.parametrize(
    "entry, result",
    [
        (10000000, "10 Mbit/s"),
        (100000000, "100 Mbit/s"),
        (1000000000, "1 Gbit/s"),
        (1400, "1.4 kbit/s"),
        (8450, "8.45 kbit/s"),
        (26430, "26.43 kbit/s"),
        (8583000, "8.58 Mbit/s"),
        (7.84e9, "7.84 Gbit/s"),
    ],
)
def test_fmt_nic_speed(entry, result) -> None:
    assert cmk.utils.render.fmt_nic_speed(entry) == result
