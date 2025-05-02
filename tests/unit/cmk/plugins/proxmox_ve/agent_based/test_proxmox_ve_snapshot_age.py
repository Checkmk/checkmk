#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import IgnoreResults, Metric, Result, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_snapshot_age import (
    check_proxmox_ve_snapshot_age,
    parse_proxmox_ve_snapshot_age,
    Section,
)


@pytest.mark.parametrize(
    "data,expected",
    [
        ('{"snaptimes": []}', {"snaptimes": []}),
        ('{"snaptimes": [1]}', {"snaptimes": [1]}),
    ],
)
def test_parse_proxmox_ve_snapshot_age(data: str, expected: Section) -> None:
    assert parse_proxmox_ve_snapshot_age([[data]]) == expected


@pytest.mark.parametrize(
    "now,params,section,expected",
    [
        (
            1,
            {"oldest_levels": ("fixed", (604800, 2592000))},
            {"snaptimes": []},
            [Result(state=State.OK, summary="No snapshot found")],
        ),
    ],
)
def test_check_proxmox_ve_snapshot_age_no_snapshot(
    now: int | float,
    params: Mapping[str, object],
    section: Section,
    expected: Sequence[IgnoreResults | Metric | Result],
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(now, tz=ZoneInfo("CET"))):
        assert list(check_proxmox_ve_snapshot_age(params, section)) == expected


@pytest.mark.parametrize(
    "params,section_data,expected_state,expected_metric",
    [
        (
            {
                "oldest_levels": ("fixed", (5000, 10000)),
            },
            {
                "snaptimes": [96_000],
            },
            State.OK,
            4000.0,
        ),
        (
            {
                "oldest_levels": ("fixed", (5000, 10000)),
            },
            {
                "snaptimes": [96_000, 94_000],
            },
            State.WARN,
            6000.0,
        ),
        (
            {
                "oldest_levels": ("fixed", (5000, 10000)),
            },
            {
                "snaptimes": [96_000, 94_000, 89_000],
            },
            State.CRIT,
            11000.0,
        ),
    ],
)
def test_check_proxmox_ve_snapshot_age_with_snapshot(
    params, section_data, expected_state, expected_metric
):
    with time_machine.travel(datetime.datetime.fromtimestamp(100_000, tz=ZoneInfo("CET"))):
        result, metric = check_proxmox_ve_snapshot_age(params, section_data)
        assert isinstance(result, Result) and isinstance(metric, Metric)
        assert result.state == expected_state
        assert metric[0] == "age" and metric[1] == expected_metric
