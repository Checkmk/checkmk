#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.agent_based.v2 import Service, StringTable
from cmk.plugins.jolokia.agent_based.jolokia_generic import discover_type, parse_jolokia_generic

info = [
    ["PingFederate-CUK-CDI", "TotalRequests", "64790", "number"],
    ["PingFederate-CUK-CDI", "MaxRequestTime", "2649", "rate"],
]


@pytest.mark.parametrize(
    "type_,lines,expected_result",
    [
        ("number", info, [Service(item="PingFederate-CUK-CDI MBean TotalRequests")]),
        ("rate", info, [Service(item="PingFederate-CUK-CDI MBean MaxRequestTime")]),
    ],
)
def test_jolokia_generic_discovery(
    type_: Literal["number", "rate"],
    lines: StringTable,
    expected_result: Sequence[Service],
) -> None:
    assert list(discover_type(type_)(parse_jolokia_generic(lines))) == expected_result
