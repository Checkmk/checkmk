#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Tuple

import pytest

from cmk.base.api.agent_based.utils import get_average, get_rate, GetRateError


@pytest.mark.parametrize(
    "pre_state,time,value,raise_of,errmsg",
    [
        ((0, 42), 0, 42, False, "No time difference"),
        ((0, 42), 0, 42, True, "No time difference"),
        ((0, 42), 1, 23, True, "Value overflow"),
        (None, 0, 42, False, "Initialized: 'foo'"),
        (None, 0, 42, True, "Initialized: 'foo'"),
    ],
)
def test_get_rate_raises(pre_state, time, value, raise_of, errmsg):
    store = {"foo": pre_state}
    with pytest.raises(GetRateError, match=errmsg):
        get_rate(store, "foo", time, value, raise_overflow=raise_of)
    assert store["foo"] == (time, value)


@pytest.mark.parametrize(
    "pre_state,time,value,raise_of,expected",
    [
        ((0, 42), 1, 42, True, 0.0),
        ((0, 23), 38, 42, True, 0.5),
        ((0, 42), 19, 23, False, -1.0),
    ],
)
def test_get_rate(pre_state, time, value, raise_of, expected):
    store = {"foo": pre_state}
    result = get_rate(store, "foo", time, value, raise_overflow=raise_of)
    assert result == expected
    assert store["foo"] == (time, value)


@pytest.mark.parametrize(
    "backlog_min,timeseries",
    [
        (
            1,
            [
                (0, 23, 23),
                (60, 42, 36.435028842544405),
                (120, 42, 39.2175144212722),
                (180, 42, 40.6087572106361),
                (240, 42, 41.30437860531805),
                (300, 42, 41.652189302659025),
            ],
        ),
        (
            3,
            [
                (0, 23, 23),
                (60, 42, 32.92116300435705),
                (120, 42, 36.63549576760762),
                (180, 42, 38.43740846859414),
                (240, 42, 39.44230522306921),
                (300, 42, 40.05645759502909),
            ],
        ),
        (
            30,
            [
                (0, 23, 23),
                (60, 42, 25.628346827556328),
                (120, 42, 27.566142090089897),
                (180, 42, 29.103887669147568),
                (240, 42, 30.36900798268354),
                (300, 42, 31.433719228839337),
            ],
        ),
    ],
)
def test_get_average(backlog_min, timeseries):
    store: Dict[str, Tuple[float, float, float]] = {}
    for idx, (this_time, this_value, expected_average) in enumerate(timeseries):
        avg = get_average(
            store,
            "foo",
            this_time,
            this_value,
            backlog_min,
        )
        assert avg == expected_average, "at [%r]: got %r expected %r" % (idx, avg, expected_average)
