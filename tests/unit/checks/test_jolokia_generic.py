#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import assertDiscoveryResultsEqual, DiscoveryResult

pytestmark = pytest.mark.checks

info = [
    ["PingFederate-CUK-CDI", "TotalRequests", "64790", "number"],
    ["PingFederate-CUK-CDI", "MaxRequestTime", "2649", "rate"],
]


@pytest.mark.parametrize(
    "check,lines,expected_result",
    [
        ("jolokia_generic", info, [("PingFederate-CUK-CDI TotalRequests", {})]),
        ("jolokia_generic.rate", info, [("PingFederate-CUK-CDI MaxRequestTime", {})]),
    ],
)
def test_jolokia_generic_discovery(check, lines, expected_result):
    parsed = Check("jolokia_generic").run_parse(lines)

    check = Check(check)
    discovered = check.run_discovery(parsed)
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(discovered),
        DiscoveryResult(expected_result),
    )
