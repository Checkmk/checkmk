#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.proxmox_ve_snapshot_age import (
    check_proxmox_ve_snapshot_age,
    parse_proxmox_ve_snapshot_age,
)


@pytest.mark.parametrize(
    "data,expected",
    [
        ('{"snaptimes": []}', {"snaptimes": []}),
        ('{"snaptimes": [1]}', {"snaptimes": [1]}),
    ],
)
def test_parse_proxmox_ve_snapshot_age(data, expected):
    assert parse_proxmox_ve_snapshot_age([[data]]) == expected


@pytest.mark.parametrize(
    "now,params,section,expected",
    [
        (
            1,
            {"oldest_levels": (604800, 2592000)},
            {"snaptimes": []},
            [Result(state=State.OK, summary="No snapshot found")],
        ),
    ],
)
def test_check_proxmox_ve_snapshot_age_no_snapshot(now, params, section, expected):
    with on_time(now, "CET"):
        assert list(check_proxmox_ve_snapshot_age(params, section)) == expected


@pytest.mark.parametrize(
    "params,section_data,expected_state,expected_metric",
    [
        (
            {
                "oldest_levels": (5000, 10000),
            },
            {
                "snaptimes": [96_000],
            },
            State.OK,
            4000.0,
        ),
        (
            {
                "oldest_levels": (5000, 10000),
            },
            {
                "snaptimes": [96_000, 94_000],
            },
            State.WARN,
            6000.0,
        ),
        (
            {
                "oldest_levels": (5000, 10000),
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
    with on_time(100_000, "CET"):
        result, metric = check_proxmox_ve_snapshot_age(params, section_data)
        assert isinstance(result, Result) and isinstance(metric, Metric)
        assert result.state == expected_state
        assert metric[0] == "age" and metric[1] == expected_metric
