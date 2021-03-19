#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]

from checktestlib import (
    CheckResult,
    assertCheckResultsEqual,
)

pytestmark = pytest.mark.checks

cisco_asa_failover_info = [
    ['Failover LAN Interface', '2', 'LAN_FO GigabitEthernet0/0.777'],
    ['Primary unit (this device)', '9', 'Active unit'],
    ['Secondary unit', '10', 'Standby unit'],
]


@pytest.mark.parametrize("info,params, expected", [
    (cisco_asa_failover_info, 1, [
        (0, 'Device (primary) is the active unit'),
        (1, '(The primary device should be other)'),
    ]),
    (cisco_asa_failover_info, 9, [
        (0, 'Device (primary) is the active unit'),
    ]),
])
def test_cisco_asa_failover_params(info, params, expected):
    check = Check('cisco_asa_failover')
    result = CheckResult(check.run_check(None, params, check.run_parse(info)))
    assertCheckResultsEqual(result, CheckResult(expected))
