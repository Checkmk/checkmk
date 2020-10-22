#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'params, result',
    [
        (
            {
                "stratum": (2, 3),
                "offset": (10, 20),  # us
            },
            (0, u'Reference clock offset: 0.9 \xb5s', [('offset', 0.9, 10, 20)])),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 20),  # us
            },
            (1, u'Reference clock offset: 0.9 \xb5s (warn/crit at 0.9/20 \xb5s)', [
                ('offset', 0.9, 0.9, 20)
            ])),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 0.9),  # us
            },
            (2, u'Reference clock offset: 0.9 \xb5s (warn/crit at 0.9/0.9 \xb5s)', [
                ('offset', 0.9, 0.9, 0.9)
            ])),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_mbg_lantime_ng_state_ref_clock(params, result):
    check = Check('mbg_lantime_ng_state')
    ref_clock_result = list(check.run_check(None, params, [[u'2', u'1', u'GPS', u'0.0009']]))[-1]
    assert ref_clock_result == result
