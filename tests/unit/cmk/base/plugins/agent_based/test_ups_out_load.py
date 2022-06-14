#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.ups_out_load import (
    check_ups_out_load,
    discovery_ups,
    parse_ups_load,
)


@pytest.mark.parametrize(
    "info, expected_result",
    [
        ([[["1", "2", "1"], ["0", "2", "2"]]], [Service(item="1")]),
    ],
)
def test_ups_out_load_discovery(info, expected_result) -> None:
    section = parse_ups_load(info)
    result = discovery_ups(section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, info, expected_result",
    [
        (
            "1",
            {"levels": (85, 90)},
            [[["1", "2", "1"]]],
            [Result(state=State.OK, summary="load: 2.00%"), Metric("out_load", 2, levels=(85, 90))],
        ),
        (
            "1",
            {"levels": (85, 90)},
            [[["1", "89", "1"]]],
            [
                Result(state=State.WARN, summary="load: 89.00% (warn/crit at 85.00%/90.00%)"),
                Metric("out_load", 89, levels=(85, 90)),
            ],
        ),
        (
            "1",
            {"levels": (85, 90)},
            [[["1", "99", "1"]]],
            [
                Result(state=State.CRIT, summary="load: 99.00% (warn/crit at 85.00%/90.00%)"),
                Metric("out_load", 99, levels=(85, 90)),
            ],
        ),
        (
            "3",
            {"levels": (85, 90)},
            [[["1", "99", "1"]]],
            [Result(state=State.UNKNOWN, summary="Phase 3 not found in SNMP output")],
        ),
        (
            "5",
            {"levels": (85, 90)},
            [[["400", "", "5"]]],
            [
                Result(state=State.OK, summary="load: 0%"),
                Metric("out_load", 0.0, levels=(85.0, 90.0)),
            ],
        ),
    ],
)
def test_ups_out_load_check(item, params, info, expected_result) -> None:
    section = parse_ups_load(info)
    result = check_ups_out_load(item, params, section)
    assert list(result) == expected_result
