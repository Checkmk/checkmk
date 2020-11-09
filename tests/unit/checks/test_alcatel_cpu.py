#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks

CHECK_NAME = "alcatel_cpu"


@pytest.mark.parametrize("info, result_expected", [
    ([[u'doesnt matter', u'doesent matter'], [u'doesnt matter']
     ], [(None, "alcatel_cpu_default_levels")]),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_inventory_function(info, result_expected):
    check = Check(CHECK_NAME)
    result = list(check.run_discovery(info))
    assert result == result_expected


@pytest.mark.parametrize("parameters, info, state_expected, infotext_expected, perfdata_expected", [
    ((30, 40), [[u'29']], 0, 'total: 29.0%', [('util', 29, 30, 40, 0, 100)]),
    ((30, 40), [[u'31']
               ], 1, 'total: 31.0% (warn/crit at 30.0%/40.0%)', [('util', 31, 30, 40, 0, 100)]),
    ((30, 40), [[u'41']
               ], 2, 'total: 41.0% (warn/crit at 30.0%/40.0%)', [('util', 41, 30, 40, 0, 100)]),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_function(parameters, info, state_expected, infotext_expected, perfdata_expected):
    """
    Verifies if check function asserts warn and crit CPU levels.
    """
    check = Check(CHECK_NAME)
    item = None
    state, infotext, perfdata = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext == infotext_expected
    assert perfdata == perfdata_expected
