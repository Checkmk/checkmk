#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils import df


@pytest.mark.parametrize(
    "params,expected",
    [
        (
            [],
            [("SUMMARY", {}), ("ceph_bar", {}), ("ceph_foo", {})],
        ),
        (
            [
                {
                    "groups": [
                        {
                            "group_name": "Foo",
                            "patterns_exclude": ["SUMM"],
                            "patterns_include": ["ceph*"],
                        }
                    ]
                }
            ],
            [("SUMMARY", {}), ("Foo", {"patterns": (["ceph*"], ["SUMM"])})],
        ),
    ],
)
def test_df_discovery(params, expected) -> None:
    actual = df.df_discovery(params, ["SUMMARY", "ceph_foo", "ceph_bar"])

    assert len(actual) == len(expected)
    for elem in expected:
        assert elem in actual


@pytest.mark.parametrize(
    ["data", "expected_result"],
    [
        pytest.param(
            (
                None,
                None,
                None,
                None,
                None,
            ),
            [
                Result(
                    state=State.OK,
                    summary="no filesystem size information",
                ),
            ],
            id="no filesystem info",
        ),
        pytest.param(
            (
                0,
                None,
                None,
                None,
                None,
            ),
            [
                Result(
                    state=State.WARN,
                    summary="Size of filesystem is 0 B",
                ),
            ],
            id="zero capacity",
        ),
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
                    summary="Inodes used: 99.83% (warn/crit at 90.00%/95.00%), Inodes available: 111 (0.17%)",
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
                    summary="Inodes used: 100.00% (warn/crit at 90.00%/95.00%), Inodes available: 0 (0%)",
                ),
            ],
            id="zero inodes left",
        ),
    ],
)
def test_df_check_filesystem_single(
    data: tuple[
        Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]
    ],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            df.df_check_filesystem_single(
                {
                    "/fake.delta": (100, 954),
                },
                "/fake",
                *data,
                df.FILESYSTEM_DEFAULT_LEVELS,
                this_time=123,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "mplist,patterns_include,patterns_exclude,expected",
    [
        (
            {
                "fake1": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
                "fake2": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
            },
            ["fake1", "fake2"],
            [],
            ["fake1", "fake2"],
        ),
        (
            {  # pylint:disable= duplicate-key
                "fake_same_name": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
                "fake_same_name": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
            },
            ["fake_same_name", "fake_same_name"],
            [],
            ["fake_same_name"],
        ),
    ],
    ids=["unique", "duplicates"],
)
def test_mountpoints_in_group(mplist, patterns_include, patterns_exclude, expected) -> None:
    """Returns list of mountpoints without duplicates."""

    result = df.mountpoints_in_group(mplist, patterns_include, patterns_exclude)

    assert isinstance(result, list)
    assert result == expected
