#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

import os
import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks

exec(open(os.path.join(os.path.dirname(__file__), '../../../checks/jolokia.include')).read())


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


def test_version_specific():
    params = {'version': ('specific', '1.6.0')}

    actual = jolokia_check_version("1.6.0", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (0, 'Jolokia 1.6.0')
    assert expected == actual

    actual = jolokia_check_version("1.3.7", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (2, 'Jolokia 1.3.7 (should be 1.6.0)')
    assert expected == actual


def test_version_at_least():
    params = {'version': ('at_least', '1.5')}

    actual = jolokia_check_version("1.5", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (0, 'Jolokia 1.5')
    assert expected == actual

    actual = jolokia_check_version("1.5.0", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (0, 'Jolokia 1.5.0')
    assert expected == actual

    actual = jolokia_check_version("1.5.1", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (0, 'Jolokia 1.5.1')
    assert expected == actual

    actual = jolokia_check_version("1.6.3", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (0, 'Jolokia 1.6.3')
    assert expected == actual

    actual = jolokia_check_version("1.3.7", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (2, 'Jolokia 1.3.7 (should be at least 1.5)')
    assert expected == actual

    actual = jolokia_check_version("1.4", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (2, 'Jolokia 1.4 (should be at least 1.5)')
    assert expected == actual


def test_version_unparseable():
    const_error = "Only characters 0-9 and . are allowed for a version."
    params = {'version': ('at_least', '1.5')}

    actual = jolokia_check_version("1.5a", params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (3, 'Can not compare 1.5a and 1.5. ' + const_error)
    assert expected == actual


def test_version_unparseable_without_wato_rule():
    params = {}
    actual = jolokia_check_version('2.x', params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (0, "Jolokia 2.x")
    assert expected == actual


def test_version_not_present():
    params = {}
    actual = jolokia_check_version(None, params, "Jolokia")  # type: ignore[name-defined] # pylint: disable=undefined-variable
    expected = (3, "Jolokia None (no agent info)")
    assert expected == actual
