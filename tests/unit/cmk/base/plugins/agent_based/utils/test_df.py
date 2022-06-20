#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional

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


@pytest.mark.parametrize(
    "filesystem_size_gb, filesystem_params, parsed_params",
    [
        pytest.param(
            10.0,
            {
                "levels": (80.0, 90.0),
            },
            {
                "levels": (80.0, 90.0),
                "levels_mb": (8 * 1024, 9 * 1024),
                "levels_text": "(warn/crit at 80.00%/90.00%)",
            },
            id="Levels expressed in percent (float) of used space",
        ),
        pytest.param(
            10.0,
            {
                "levels": (-20.0, -10.0),
            },
            {
                "levels": (-20.0, -10.0),
                "levels_mb": ((-2) * 1024, (-1) * 1024),
                "levels_text": "(warn/crit at free space below 20.00%/10.00%)",
            },
            id="Levels expressed in percent (float) of free space",
        ),
        pytest.param(
            10.0,
            {
                "levels": (8 * 1024, 9 * 1024),
            },
            {
                "levels": (8 * 1024, 9 * 1024),
                "levels_mb": (8 * 1024, 9 * 1024),
                "levels_text": "(warn/crit at 8.00 GiB/9.00 GiB)",
            },
            id="Levels expressed in MB (int) of used space",
        ),
        pytest.param(
            10.0,
            {
                "levels": ((-2) * 1024, (-1) * 1024),
            },
            {
                "levels": ((-2) * 1024, (-1) * 1024),
                "levels_mb": ((-2) * 1024, (-1) * 1024),
                "levels_text": "(warn/crit at free space below 2.00 GiB/1.00 GiB)",
            },
            id="Levels expressed in MB (int) of free space",
        ),
        pytest.param(
            10.0,
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (15.0 * 1024**3, (60.0, 70.0)),
                ],
            },
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (15.0 * 1024**3, (60.0, 70.0)),
                ],
                "levels_mb": (4 * 1024, 5 * 1024),
                "levels_text": "(warn/crit at 4.00 GiB/5.00 GiB)",
            },
            id=(
                "Different levels for different sizes of filesystems. "
                "For a filesystem in the range of two filesystem size "
                "configurations, the configuration of the smaller filesystem is "
                "applied. Note it is possible to have both percent and absolute "
                "as levels in the same list."
            ),
        ),
        pytest.param(
            10.0,
            {
                "levels": [
                    (15.0 * 1024**3, (60.0, 70.0)),
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                ],
            },
            {
                "levels": [
                    (15.0 * 1024**3, (60.0, 70.0)),
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                ],
                "levels_mb": (4 * 1024, 5 * 1024),
                "levels_text": "(warn/crit at 4.00 GiB/5.00 GiB)",
            },
            id=("The order of filesystem sizes in the list of levels does not matter."),
        ),
        pytest.param(
            10.0,
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (10.0 * 1024**3, (60.0, 70.0)),
                ],
            },
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (10.0 * 1024**3, (60.0, 70.0)),
                ],
                "levels_mb": (4 * 1024, 5 * 1024),
                "levels_text": "(warn/crit at 4.00 GiB/5.00 GiB)",
            },
            id=(
                "The levels of the filesystem size 10GB are not applied to "
                "filesystems that are exactly 10GB in size, as the configuration "
                "specifies filesystems need to be greater than in order for the "
                "levels to apply."
            ),
        ),
        pytest.param(
            1.0,
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (10.0 * 1024**3, (60.0, 70.0)),
                ],
            },
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (10.0 * 1024**3, (60.0, 70.0)),
                ],
                "levels_mb": (1 * 1024, 1 * 1024),
                "levels_text": "(warn/crit at 100.00%/100.00%)",
            },
            id=(
                "If the filesystem size cannot be determined, levels revert to 100% "
                "for WARN/CRIT. TODO: defaults should be used instead."
            ),
        ),
    ],
)
def test_get_filesystem_levels(
    filesystem_size_gb: float,
    filesystem_params: Mapping[str, Any],
    parsed_params: Mapping[str, Any],
) -> None:
    actual_parsed_params = df.get_filesystem_levels(filesystem_size_gb, filesystem_params)

    assert actual_parsed_params["levels"] == parsed_params["levels"]
    assert actual_parsed_params["levels_mb"] == parsed_params["levels_mb"]
    assert actual_parsed_params["levels_text"] == parsed_params["levels_text"]


@pytest.mark.parametrize(
    "filesystem_size_gb, filesystem_params, parsed_params",
    [
        pytest.param(
            100.0,
            {
                "levels": (80.0, 90.0),
                "magic": 0.8,
                "levels_low": (60.0, 70.0),
                "magic_normsize": 100.0,
            },
            {
                "levels": (80.0, 90.0),
                "levels_mb": (
                    80.0 * 1024,
                    90.0 * 1024,
                ),
                "levels_text": "(warn/crit at 80.00%/90.00%)",
            },
            id=(
                "Provided levels are applied without adjustment when reference size (aka 'magic normsize') is the same as filesystem size."
            ),
        ),
        pytest.param(
            100.0,
            {
                "levels": (80.0, 90.0),
                "magic": 1,
                "levels_low": (60.0, 70.0),
                "magic_normsize": 20.0,
            },
            {
                "levels": (80.0, 90.0),
                "levels_mb": (
                    80.0 * 1024,
                    90.0 * 1024,
                ),
                "levels_text": "(warn/crit at 80.00%/90.00%)",
            },
            id=("Provided levels are applied without adjustment when MF is exactly equal 1."),
        ),
        pytest.param(
            100.0,
            {
                "levels": (80.0, 90.0),
                "magic": 0.8,
                "levels_low": (60.0, 70.0),
                "magic_normsize": 20.0,
            },
            {
                "levels": (80.0, 90.0),
                "levels_mb": (
                    85.0 * 1024,
                    93.0 * 1024,
                ),
                "levels_text": "(warn/crit at 85.50%/92.75%)",
            },
            id=("Magic factor adjusts levels."),
        ),
        pytest.param(
            100.0,
            {
                "levels": (80 * 1024, 90 * 1024),
                "magic": 0.8,
                "levels_low": (60.0, 70.0),
                "magic_normsize": 20.0,
            },
            {
                "levels": (
                    80 * 1024,
                    90 * 1024,
                ),
                "levels_mb": (
                    85 * 1024,
                    93 * 1024,
                ),
                "levels_text": "(warn/crit at 85.50%/92.75%)",
            },
            id=("Magic factor adjusts absolute levels."),
        ),
        pytest.param(
            100.0,
            {
                "levels": (80.0, 90.0),
                "magic": 0.1,
                "levels_low": (60.0, 70.0),
                "magic_normsize": 1000.0,
            },
            {
                "levels": (80.0, 90.0),
                "levels_mb": (
                    60 * 1024,
                    70 * 1024,
                ),
                "levels_text": "(warn/crit at 60.00%/70.00%)",
            },
            id=("Magic factor does not adjust levels below minimum levels (aka 'levels low')."),
        ),
        pytest.param(
            100.0,
            {
                "levels": (-40.0, -30.0),
                "magic": 0.8,
                "levels_low": (10.0, 20.0),
                "magic_normsize": 100.0,
            },
            {
                "levels": (-40.0, -30.0),
                "levels_mb": (
                    10 * 1024,
                    20 * 1024,
                ),
                "levels_text": "(warn/crit at 10.00%/20.00%)",
            },
            id=(
                "Minimum levels (aka 'levels low') do not make sense when levels are specified as free space. They are "
                "assumed to be relating to used space. TODO: fix this behaviour..."
            ),
        ),
    ],
)
def test_get_filesystem_levels_magic_factor(
    filesystem_size_gb: float,
    filesystem_params: Mapping[str, Any],
    parsed_params: Mapping[str, Any],
) -> None:
    actual_parsed_params = df.get_filesystem_levels(filesystem_size_gb, filesystem_params)

    assert actual_parsed_params["levels"] == parsed_params["levels"]
    assert actual_parsed_params["levels_mb"] == pytest.approx(parsed_params["levels_mb"], rel=0.01)
    assert actual_parsed_params["levels_text"] == parsed_params["levels_text"]


@pytest.mark.parametrize(
    "filesystem_params, parsed_params",
    [
        pytest.param(
            {
                "inodes_levels": (80.0, 90.0),
            },
            {
                "inodes_levels": (80.0, 90.0),
            },
            id="Levels expressed in percent (float) of free inodes",
        ),
        pytest.param(
            {
                "inodes_levels": (50, 100),
            },
            {
                "inodes_levels": (50, 100),
            },
            id="Levels expressed in count (int) of free inodes",
        ),
        pytest.param(
            {
                "inodes_levels": None,
            },
            {
                "inodes_levels": (None, None),
            },
            id="Levels set to 'ignore' have a None value",
        ),
        pytest.param(
            {},
            {
                "inodes_levels": (10.0, 5.0),
            },
            id=("Levels for inodes are not configured: defaults are used."),
        ),
    ],
)
def test_get_filesystem_levels_inodes(
    filesystem_params: Mapping[str, Any],
    parsed_params: Mapping[str, Any],
) -> None:
    actual_parsed_params = df.get_filesystem_levels(10.0, filesystem_params)

    assert actual_parsed_params["inodes_levels"] == parsed_params["inodes_levels"]
