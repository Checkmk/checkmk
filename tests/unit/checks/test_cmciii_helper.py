#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from testlib import Check  # type: ignore[import]
import pytest


@pytest.mark.parametrize("variable, expected", [
    ("one.two", ["one", "", "two"]),
    ("one.two.three", ["one", "two", "three"]),
    ("Phase.two", ["", "Phase", "", "two"]),
    ("Phase.two.three", ["", "Phase", "two", "three"]),
])
def test_cmciii_container(variable, expected):
    sanitize_variable = Check('cmciii').context['sanitize_variable']
    assert sanitize_variable(variable) == expected


@pytest.mark.parametrize("variable", [
    "",
    "one",
])
def test_cmciii_container_raises(variable):
    sanitize_variable = Check('cmciii').context['sanitize_variable']
    with pytest.raises(IndexError):
        sanitize_variable(variable)


@pytest.mark.parametrize("table, container, var_type, variable_end, expected", [
    ("not_phase", [], "", "var_end", "var_end"),
    ("phase", ["ONE", "TWO", "THREE", "FOUR", "FIVE"], "2", "", "four_five"),
    ("phase", ["ONE", "TWO", "THREE", "FOUR", "FIVE"], "not 2", "", "FOUR FIVE"),
])
def test_sensor_key(table, container, var_type, variable_end, expected):
    sensor_key = Check('cmciii').context['sensor_key']
    assert sensor_key(table, container, var_type, variable_end) == expected
