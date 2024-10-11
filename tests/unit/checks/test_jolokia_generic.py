#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import StringTable

from .checktestlib import assertDiscoveryResultsEqual, Check, DiscoveryResult

pytestmark = pytest.mark.checks

info = [
    ["PingFederate-CUK-CDI", "TotalRequests", "64790", "number"],
    ["PingFederate-CUK-CDI", "MaxRequestTime", "2649", "rate"],
]


@pytest.mark.parametrize(
    "check,lines,expected_result",
    [
        ("jolokia_generic", info, [("PingFederate-CUK-CDI MBean TotalRequests", {})]),
        ("jolokia_generic_rate", info, [("PingFederate-CUK-CDI MBean MaxRequestTime", {})]),
    ],
)
def test_jolokia_generic_discovery(
    check: str, lines: StringTable, expected_result: Sequence[tuple[str, dict[str, object]]]
) -> None:
    parsed = Check("jolokia_generic").run_parse(lines)

    check_val = Check(check)
    discovered = check_val.run_discovery(parsed)
    assertDiscoveryResultsEqual(
        check_val,
        DiscoveryResult(discovered),
        DiscoveryResult(expected_result),
    )
