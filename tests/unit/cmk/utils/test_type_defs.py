#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from ast import literal_eval

import pytest  # type: ignore[import]

from cmk.utils.type_defs import EvalableFloat

from cmk.snmplib.type_defs import OIDBytes, OIDSpec


@pytest.mark.parametrize("value", [3, ("foo", "bar")])
def test_oidspec_invalid_type(value):
    with pytest.raises(TypeError):
        _ = OIDSpec(value)


@pytest.mark.parametrize("value", ["", "foo", "1."])
def test_oidspec_invalid_value(value):
    with pytest.raises(ValueError):
        _ = OIDSpec(value)


@pytest.mark.parametrize("value", ["foo", 1])
def test_oidspec_invalid_adding_type(value):
    oid = OIDSpec(".1.2.3")
    with pytest.raises(TypeError):
        _ = oid + value


@pytest.mark.parametrize("left, right", [
    (OIDBytes("4.5"), OIDBytes("4.5")),
    (OIDSpec(".1.2.3"), OIDSpec(".1.2.3")),
])
def test_oidspec_invalid_adding_value(left, right):
    with pytest.raises(ValueError):
        _ = left + right


def test_oidspec():
    oid_base = OIDSpec(".1.2.3")
    oid_column = OIDBytes("4.5")

    assert str(oid_base) == ".1.2.3"
    assert str(oid_column) == "4.5"

    assert repr(oid_base) == "OIDSpec('.1.2.3')"
    assert repr(oid_column) == "OIDBytes('4.5')"

    oid_sum = oid_base + oid_column
    assert isinstance(oid_sum, OIDBytes)
    assert str(oid_sum) == ".1.2.3.4.5"


def test_evalable_float():
    inf = EvalableFloat('inf')
    assert literal_eval("%r" % inf) == float('inf')
