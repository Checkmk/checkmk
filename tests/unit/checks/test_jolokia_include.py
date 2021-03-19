#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore[import]

from cmk.base.check_legacy_includes.jolokia import *
pytestmark = pytest.mark.checks


@pytest.mark.parametrize('line,length,result', [
    (list('ABCDEF'), 3, ["A", "B C D E", "F"]),
    (list('ABCDEF'), 4, ["A", "B C D", "E", "F"]),
    (list('AB'), 2, list("AB")),
])
def test_jolokia_basic_split(line, length, result):
    split_up = jolokia_basic_split(line, length)  # type: ignore[name-defined] # pylint: disable=undefined-variable
    assert result == split_up


@pytest.mark.parametrize('line,length', [
    (['too', 'short'], 3),
    (['too', 'short', 'aswell'], 4),
])
def test_jolokia_basic_split_fail_value(line, length):
    with pytest.raises(ValueError):
        jolokia_basic_split(line, length)  # type: ignore[name-defined] # pylint: disable=undefined-variable


@pytest.mark.parametrize('line,length', [
    (['too', 'short'], 1),
])
def test_jolokia_basic_split_fail_notimplemented(line, length):
    with pytest.raises(NotImplementedError):
        jolokia_basic_split(line, length)  # type: ignore[name-defined] # pylint: disable=undefined-variable
