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
def test_sanitize_variable(variable, expected):
    sanitize_variable = Check('cmciii').context['sanitize_variable']
    assert sanitize_variable(variable) == expected


@pytest.mark.parametrize("variable", [
    "",
    "one",
])
def test_sanitize_variable_raises(variable):
    sanitize_variable = Check('cmciii').context['sanitize_variable']
    with pytest.raises(IndexError):
        sanitize_variable(variable)


@pytest.mark.parametrize("table, var_type, variable, expected", [
    ("not_phase", "", ["var_end"], "var_end"),
    ("phase", "2", ["ONE", "TWO", "THREE", "FOUR", "FIVE", "END"], "three_four_five"),
    ("phase", "not 2", ["ONE", "TWO", "THREE", "FOUR", "FIVE", "END"], "THREE FOUR FIVE"),
])
def test_sensor_key(table, var_type, variable, expected):
    sensor_key = Check('cmciii').context['sensor_key']
    assert sensor_key(table, var_type, variable) == expected


@pytest.mark.parametrize("sensor_type, variable, expected", [
    ("temp", ["FooTemperature", "Var"], "Foo device"),
    ("temp", ["Temperature", "In-Var"], "Ambient device In"),
    ("temp", ["Temperature", "Out-Var"], "Ambient device Out"),
    ("phase", ["", "Phase L A"], "device Phase A"),
    ("phase", ["one", "Phase L A"], "device one Phase A"),
    ("psm_plugs", ["one", "two"], "device one.two"),
    ("can_current", ["one", "two"], "device one.two"),
    ("other_sensors", ["one"], "device one"),
    ("other_sensors", ["one", "two"], "device one"),
])
def test_sensor_item(sensor_type, variable, expected):
    sensor_item = Check('cmciii').context['sensor_item']
    assert sensor_item(sensor_type, variable, "device") == expected


def test_sensor_item_temp_in_out():
    sensor_item = Check('cmciii').context['sensor_item']
    assert sensor_item('temp_in_out', ['Air'], 'Liquid_Cooling_Package') == 'Air LCP'
