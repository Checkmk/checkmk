#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.cisco_cpu_multiitem import (
    check_cisco_cpu_multiitem,
    discover_cisco_cpu_multiitem,
    DISCOVERY_DEFAULT_PARAMETERS,
    Params,
    parse_cisco_cpu_multiitem,
    Section,
)


@pytest.fixture(name="parsed_section")
def parsed_section_fixture() -> Section:
    return parse_cisco_cpu_multiitem(
        [[["2001", "5"], ["3001", "10"]], [["2001", "cpu 2"], ["3001", "another cpu 3"]]]
    )


def test_check_cisco_cpu_multiitem(parsed_section: Section) -> None:
    params = Params({"levels": (80, 90)})

    assert list(check_cisco_cpu_multiitem("2", params, parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 5.00%"),
        Metric("util", 5.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(check_cisco_cpu_multiitem("another cpu 3", params, parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 10.00%"),
        Metric("util", 10.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(check_cisco_cpu_multiitem("average", params, parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 7.50%"),
        Metric("util", 7.5, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(check_cisco_cpu_multiitem("not_found", params, parsed_section)) == []


@pytest.mark.parametrize(
    "discovery_params, expected_discovery_result",
    (
        pytest.param(
            DISCOVERY_DEFAULT_PARAMETERS,
            [
                Service(item="2"),
                Service(item="another cpu 3"),
            ],
            id="default discovery params: individual only",
        ),
        pytest.param(
            {"individual": False, "average": True},
            [
                Service(item="average"),
            ],
            id="discover average only",
        ),
        pytest.param(
            {"individual": True, "average": True},
            [
                Service(item="2"),
                Service(item="another cpu 3"),
                Service(item="average"),
            ],
            id="discover both: average and individual",
        ),
        pytest.param(
            {"individual": False, "average": False},
            [],
            id="discover none",
        ),
    ),
)
def test_discover_cisco_cpu_multiitem(
    parsed_section: Section, discovery_params, expected_discovery_result
) -> None:
    assert (
        list(discover_cisco_cpu_multiitem(discovery_params, parsed_section))
        == expected_discovery_result
    )
