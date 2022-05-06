#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from typing import Optional, Tuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils import df

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('size_gb, params, expected_levels', [
    (
        2.0,
        {
            'levels': (80.0, 90.0),
        },
        {
            'inodes_levels': (None, None),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1638.4, 1843.2),
            'levels_text': '(warn/crit at 80.00%/90.00%)',
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
    (
        2.0,
        {
            'levels': (1500, 2000),
        },
        {
            'inodes_levels': (None, None),
            'levels': (1500, 2000),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1500.0, 2000.0),
            'levels_text': '(warn/crit at 1.46 GiB/1.95 GiB)',
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
    (
        2.0,
        {
            'levels': (80.0, 90.0),
            'magic': 0.9,
        },
        {
            'inodes_levels': (None, None),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1532.344151329109, 1790.1720756645545),
            'levels_text': '(warn/crit at 74.82%/87.41%)',
            'magic': 0.9,
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
    (
        2.0,
        {
            'levels': (1500, 2000),
            'magic': 0.9,
        },
        {
            'inodes_levels': (None, None),
            'levels': (1500, 2000),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1358.1088743367964, 1987.57158023388),
            'levels_text': '(warn/crit at 66.31%/97.05%)',
            'magic': 0.9,
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
])
def test_get_filesystem_levels(size_gb, params, expected_levels):
    levels = df.get_filesystem_levels(size_gb, params)
    assert levels == expected_levels


@pytest.mark.parametrize(
    ["data", "expected_result"],
    [
        pytest.param(
            (
                102655,
                58814,
                122,
                None,
                None,
            ),
            [
                Metric(
                    "fs_used",
                    43841.0,
                    levels=(82124.0, 92389.5),
                    boundaries=(0.0, 102655.0),
                ),
                Metric(
                    "fs_size",
                    102655.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    42.707125809751105,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.OK,
                    summary="42.71% used (42.8 of 100 GiB)",
                ),
                Metric(
                    "growth",
                    161105947.82608697,
                ),
                Result(
                    state=State.OK,
                    summary="trend per 1 day 0 hours: +154 TiB",
                ),
                Result(
                    state=State.OK,
                    summary="trend per 1 day 0 hours: +156939.21%",
                ),
                Metric(
                    "trend",
                    161105947.82608697,
                    boundaries=(0.0, 4277.291666666667),
                ),
                Result(
                    state=State.OK,
                    summary="Time left until disk full: 32 seconds",
                ),
            ],
            id="no inode information",
        ),
        pytest.param(
            (
                102655,
                58814,
                122,
                65486,
                111,
            ),
            [
                Metric(
                    "fs_used",
                    43841.0,
                    levels=(82124.0, 92389.5),
                    boundaries=(0.0, 102655.0),
                ),
                Metric(
                    "fs_size",
                    102655.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    42.707125809751105,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.OK,
                    summary="42.71% used (42.8 of 100 GiB)",
                ),
                Metric(
                    "growth",
                    161105947.82608697,
                ),
                Result(
                    state=State.OK,
                    summary="trend per 1 day 0 hours: +154 TiB",
                ),
                Result(
                    state=State.OK,
                    summary="trend per 1 day 0 hours: +156939.21%",
                ),
                Metric(
                    "trend",
                    161105947.82608697,
                    boundaries=(0.0, 4277.291666666667),
                ),
                Result(
                    state=State.OK,
                    summary="Time left until disk full: 32 seconds",
                ),
                Metric(
                    "inodes_used",
                    65375.0,
                    levels=(58937.4, 62211.7),
                    boundaries=(0.0, 65486.0),
                ),
                Result(
                    state=State.CRIT,
                    summary=
                    "Inodes used: 99.83% (warn/crit at 90.00%/95.00%), Inodes available: 111 (0.17%)",
                ),
            ],
            id="with inode information",
        ),
        pytest.param(
            (
                102655,
                58814,
                122,
                65486,
                0,
            ),
            [
                Metric(
                    "fs_used",
                    43841.0,
                    levels=(82124.0, 92389.5),
                    boundaries=(0.0, 102655.0),
                ),
                Metric(
                    "fs_size",
                    102655.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    42.707125809751105,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.OK,
                    summary="42.71% used (42.8 of 100 GiB)",
                ),
                Metric(
                    "growth",
                    161105947.82608697,
                ),
                Result(
                    state=State.OK,
                    summary="trend per 1 day 0 hours: +154 TiB",
                ),
                Result(
                    state=State.OK,
                    summary="trend per 1 day 0 hours: +156939.21%",
                ),
                Metric(
                    "trend",
                    161105947.82608697,
                    boundaries=(0.0, 4277.291666666667),
                ),
                Result(
                    state=State.OK,
                    summary="Time left until disk full: 32 seconds",
                ),
                Metric(
                    "inodes_used",
                    65486.0,
                    levels=(58937.4, 62211.7),
                    boundaries=(0.0, 65486.0),
                ),
                Result(
                    state=State.CRIT,
                    summary=
                    "Inodes used: 100.00% (warn/crit at 90.00%/95.00%), Inodes available: 0 (0%)",
                ),
            ],
            id="zero inodes left",
        ),
    ],
)
def test_df_check_filesystem_single(
    data: Tuple[float, float, float, Optional[float], Optional[float]],
    expected_result: CheckResult,
) -> None:
    assert (list(
        df.df_check_filesystem_single(
            {
                "/fake.delta": (100, 954),
            },
            "/fake",
            *data,
            df.FILESYSTEM_DEFAULT_LEVELS,
            this_time=123,
        )) == expected_result)
