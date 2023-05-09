#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO (mo): move this where it belongs

from ast import literal_eval

import pytest  # type: ignore[import]

from cmk.utils.type_defs import EvalableFloat

from cmk.base.api.agent_based.section_classes import OIDBytes, OIDCached, SNMPTree


@pytest.mark.parametrize("value", [3, ("foo", "bar")])
def test_oidspec_invalid_type(value):
    with pytest.raises(TypeError):
        SNMPTree.validate_oid_string(value)


@pytest.mark.parametrize("value", ["", "foo", "1."])
def test_oidspec_invalid_value(value):
    with pytest.raises(ValueError):
        SNMPTree.validate_oid_string(value)


def test_oidspec():
    oid_c = OIDCached("1.2.3")
    oid_b = OIDBytes("4.5")

    assert repr(oid_c) == "OIDCached('1.2.3')"
    assert repr(oid_b) == "OIDBytes('4.5')"


def test_evalable_float():
    inf = EvalableFloat('inf')
    assert literal_eval("%r" % inf) == float('inf')
