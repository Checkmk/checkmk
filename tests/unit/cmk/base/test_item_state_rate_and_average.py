#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import pytest

from cmk.base import item_state


@pytest.mark.parametrize(
    "pre_state,time,value,errmsg",
    [
        ((0, 42), 0, 42, "No time difference"),
        ((0, 42), 1, 23, "Value overflow"),
        (None, 0, 42, "Counter initialization"),
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_get_rate_raises(pre_state, time, value, errmsg):
    item_state.set_item_state("foo", pre_state)
    with pytest.raises(item_state.MKCounterWrapped, match=errmsg):
        item_state.get_rate("foo", time, value, onwrap=item_state.RAISE)


@pytest.mark.parametrize(
    "pre_state,time,value,onwrap,expected",
    [
        ((0, 42), 1, 42, item_state.RAISE, 0.0),
        (None, 1, 42, item_state.ZERO, 0.0),
        (None, 1, 42, item_state.SKIP, 0.0),
        ((0, 23), 38, 42, item_state.RAISE, 0.5),
        ((0, 42), 19, 23, item_state.RAISE, -1.0),
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_get_rate(pre_state, time, value, onwrap, expected):
    item_state.set_item_state("foo", pre_state)
    result = item_state.get_rate("foo", time, value, onwrap=onwrap, allow_negative=True)
    assert result == expected


@pytest.mark.parametrize(
    "ini_zero,backlog_min,timeseries",
    [
        (
            True,
            3,
            [
                (0, 23, 0),
                (60, 23, 4.744887902365705),
                (120, 23, 8.510907926208958),
                (180, 23, 11.5),
                (240, 23, 13.872443951182852),
                (300, 23, 15.755453963104479),
                (360, 23, 17.25),
                (420, 23, 18.436221975591426),
                (480, 23, 19.37772698155224),
                (540, 23, 20.125),
            ],
        ),
        (
            False,
            3,
            [
                (0, 23, 23),
                (60, 23, 23.0),
                (120, 23, 23.0),
            ],
        ),
        (
            False,
            3,
            [
                (0, 42, 42),
                (60000, 2, 2.0),
            ],
        ),
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_get_average(ini_zero, backlog_min, timeseries):
    for _idx, (this_time, this_value, expected_average) in enumerate(timeseries):
        avg = item_state.get_average(
            "foo",
            this_time,
            this_value,
            backlog_min,
            initialize_zero=ini_zero,
        )
        assert avg == expected_average
