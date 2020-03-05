#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks

CHECK_NAME = "alcatel_fans"


@pytest.mark.parametrize("info, result_expected", [
    ([[u'doesnt matter']], [(1, None)]),
    ([[u'doesnt matter', u'doesent matter'], [u'doesnt matter']], [(1, None), (2, None)]),
])
def test_inventory_function(check_manager, info, result_expected):
    check = check_manager.get_check(CHECK_NAME)
    result = list(check.run_discovery(info))
    assert result == result_expected


@pytest.mark.parametrize(
    "parameters, item, info, state_expected, infotext_expected, perfdata_expected", [
        ((0, 0), 1, [[u'0']], 2, 'Fan has no status', None),
        ((0, 0), 1, [[u'1']], 2, 'Fan not running', None),
        ((0, 0), 1, [[u'2']], 0, 'Fan running', None),
    ])
def test_check_function(check_manager, parameters, item, info, state_expected, infotext_expected,
                        perfdata_expected):
    """
    Verifies if check function asserts warn and crit Board and CPU temperature levels.
    """
    check = check_manager.get_check(CHECK_NAME)
    state, infotext = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext_expected in infotext
