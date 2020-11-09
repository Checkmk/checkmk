#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from checktestlib import assertDiscoveryResultsEqual, DiscoveryResult

pytestmark = pytest.mark.checks

info = [[u'PingFederate-CUK-CDI', u'TotalRequests', u'64790', u'number'],
        [u'PingFederate-CUK-CDI', u'MaxRequestTime', u'2649', u'rate']]


@pytest.mark.parametrize("check,lines,expected_result", [
    ('jolokia_generic', info, [(u'PingFederate-CUK-CDI TotalRequests', {})]),
    ('jolokia_generic.rate', info, [(u'PingFederate-CUK-CDI MaxRequestTime', {})]),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_jolokia_generic_discovery(check, lines, expected_result):
    parsed = Check('jolokia_generic').run_parse(lines)

    check = Check(check)
    discovered = check.run_discovery(parsed)
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(discovered),
        DiscoveryResult(expected_result),
    )
