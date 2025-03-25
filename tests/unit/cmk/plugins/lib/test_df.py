#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.lib import df


@pytest.mark.parametrize(
    "params,expected",
    [
        (
            [],
            [Service(item="SUMMARY"), Service(item="ceph_bar"), Service(item="ceph_foo")],
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
            [
                Service(item="SUMMARY"),
                Service(item="Foo", parameters={"patterns": (["ceph*"], ["SUMM"])}),
            ],
        ),
    ],
)
def test_df_discovery(
    params: Iterable[Mapping[str, object]],
    expected: Sequence[Service],
) -> None:
    actual = list(df.df_discovery(params, ["SUMMARY", "ceph_foo", "ceph_bar"]))

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
                Metric("fs_free", 58814.0, boundaries=(0, None)),
                Metric(
                    "fs_used_percent",
                    42.707125809751105,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.OK,
                    summary="Used: 42.71% - 42.8 GiB of 100 GiB",
                ),
                Metric("fs_size", 102655.0, boundaries=(0.0, None)),
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
                    "fs_free",
                    58814.0,
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
                    summary="Used: 42.71% - 42.8 GiB of 100 GiB",
                ),
                Metric("fs_size", 102655.0, boundaries=(0.0, None)),
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
                    "fs_free",
                    58814.0,
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
                    summary="Used: 42.71% - 42.8 GiB of 100 GiB",
                ),
                Metric("fs_size", 102655.0, boundaries=(0.0, None)),
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
    data: tuple[float | None, float | None, float | None, float | None, float | None],
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
                df.FILESYSTEM_DEFAULT_PARAMS,
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
            {
                "fake_same_name": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
                "fake_same_name": {  # noqa: F601
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
def test_mountpoints_in_group(
    mplist: Iterable[str],
    patterns_include: Sequence[str],
    patterns_exclude: Sequence[str],
    expected: Sequence[str],
) -> None:
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(80.0),
                crit_percent=df.Percent(90.0),
                warn_absolute=df.Bytes(8 * 1024**3),
                crit_absolute=df.Bytes(9 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
            id="Levels expressed in percent (float) of used space",
        ),
        pytest.param(
            10.0,
            {
                "levels": (-20.0, -10.0),
            },
            df.LevelsFreeSpace(
                warn_percent=df.Percent(-20.0),
                crit_percent=df.Percent(-10.0),
                warn_absolute=df.Bytes((-2) * 1024**3),
                crit_absolute=df.Bytes((-1) * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
            id="Levels expressed in percent (float) of free space",
        ),
        pytest.param(
            10.0,
            {
                "levels": (8 * 1024, 9 * 1024),
            },
            df.LevelsUsedSpace(
                warn_percent=df.Percent(80.0),
                crit_percent=df.Percent(90.0),
                warn_absolute=df.Bytes(8 * 1024**3),
                crit_absolute=df.Bytes(9 * 1024**3),
                render_as=df.RenderOptions.bytes_,
            ),
            id="Levels expressed in MB (int) of used space",
        ),
        pytest.param(
            10.0,
            {
                "levels": ((-2) * 1024, (-1) * 1024),
            },
            df.LevelsFreeSpace(
                warn_percent=df.Percent(-20.0),
                crit_percent=df.Percent(-10.0),
                warn_absolute=df.Bytes((-2) * 1024**3),
                crit_absolute=df.Bytes((-1) * 1024**3),
                render_as=df.RenderOptions.bytes_,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(40.0),
                crit_percent=df.Percent(50.0),
                warn_absolute=df.Bytes(4 * 1024**3),
                crit_absolute=df.Bytes(5 * 1024**3),
                render_as=df.RenderOptions.bytes_,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(40.0),
                crit_percent=df.Percent(50.0),
                warn_absolute=df.Bytes(4 * 1024**3),
                crit_absolute=df.Bytes(5 * 1024**3),
                render_as=df.RenderOptions.bytes_,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(40.0),
                crit_percent=df.Percent(50.0),
                warn_absolute=df.Bytes(4 * 1024**3),
                crit_absolute=df.Bytes(5 * 1024**3),
                render_as=df.RenderOptions.bytes_,
            ),
            id=(
                "The levels of the filesystem size 10GB are not applied to "
                "filesystems that are exactly 10GB in size, as the configuration "
                "specifies filesystems need to be greater than in order for the "
                "levels to apply."
            ),
        ),
        pytest.param(
            20.0,
            {
                "levels": [
                    (5.0 * 1024**3, (4 * 1024, 5 * 1024)),
                    (10.0 * 1024**3, (60.0, 70.0)),
                ],
            },
            df.LevelsUsedSpace(
                warn_percent=df.Percent(60.0),
                crit_percent=df.Percent(70.0),
                warn_absolute=df.Bytes(int((20.0 * 1024**3) * 0.6)),
                crit_absolute=df.Bytes(int((20 * 1024**3) * 0.7)),
                render_as=df.RenderOptions.percent,
            ),
            id=(
                "The levels for the greatest filesystem size in the list are "
                "applied regardless of how large the filesystem is."
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(100.0),
                crit_percent=df.Percent(100.0),
                warn_absolute=df.Bytes(1 * 1024**3),
                crit_absolute=df.Bytes(1 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
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
    parsed_params: df.FilesystemLevels,
) -> None:
    actual_parsed_params = df.get_filesystem_levels(
        filesystem_size_gb, {**df.FILESYSTEM_DEFAULT_PARAMS, **filesystem_params}
    )

    assert actual_parsed_params == parsed_params


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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(80.0),
                crit_percent=df.Percent(90.0),
                warn_absolute=df.Bytes(80 * 1024**3),
                crit_absolute=df.Bytes(90 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(80.0),
                crit_percent=df.Percent(90.0),
                warn_absolute=df.Bytes(80 * 1024**3),
                crit_absolute=df.Bytes(90 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(85.0),
                crit_percent=df.Percent(93.0),
                warn_absolute=df.Bytes(85 * 1024**3),
                crit_absolute=df.Bytes(93 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(85.0),
                crit_percent=df.Percent(93.0),
                warn_absolute=df.Bytes(85 * 1024**3),
                crit_absolute=df.Bytes(93 * 1024**3),
                render_as=df.RenderOptions.bytes_,
            ),
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
            df.LevelsUsedSpace(
                warn_percent=df.Percent(60.0),
                crit_percent=df.Percent(70.0),
                warn_absolute=df.Bytes(60 * 1024**3),
                crit_absolute=df.Bytes(70 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
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
            df.LevelsFreeSpace(
                warn_percent=df.Percent(10.0),
                crit_percent=df.Percent(20.0),
                warn_absolute=df.Bytes(10 * 1024**3),
                crit_absolute=df.Bytes(20 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
            id=(
                "Minimum levels (aka 'levels low') do not make sense when levels are specified as free space. They are "
                "assumed to be relating to used space. This behaviour only happens when the magic factor is not equal to 1.0."
                "TODO: fix this behaviour..."
            ),
        ),
        pytest.param(
            100.0,
            {
                "levels": (-40.0, -30.0),
                "magic": 1.0,
                "levels_low": (10.0, 20.0),
                "magic_normsize": 100.0,
            },
            df.LevelsFreeSpace(
                warn_percent=df.Percent(-40.0),
                crit_percent=df.Percent(-30.0),
                warn_absolute=df.Bytes(-40 * 1024**3),
                crit_absolute=df.Bytes(-30 * 1024**3),
                render_as=df.RenderOptions.percent,
            ),
            id=("When the magic factor is equal to 1.0, the levels are interpreted correctly."),
        ),
    ],
)
def test_get_filesystem_levels_magic_factor(
    filesystem_size_gb: float,
    filesystem_params: Mapping[str, Any],
    parsed_params: df.FilesystemLevels,
) -> None:
    actual_parsed_params = df.get_filesystem_levels(
        filesystem_size_gb, {**df.FILESYSTEM_DEFAULT_PARAMS, **filesystem_params}
    )

    assert actual_parsed_params.warn_percent == pytest.approx(parsed_params.warn_percent, abs=1)
    assert actual_parsed_params.crit_percent == pytest.approx(parsed_params.crit_percent, abs=1)
    assert actual_parsed_params.warn_absolute == pytest.approx(
        parsed_params.warn_absolute, rel=0.01
    )
    assert actual_parsed_params.crit_absolute == pytest.approx(
        parsed_params.crit_absolute, rel=0.01
    )
    assert actual_parsed_params.render_as == parsed_params.render_as


@pytest.mark.parametrize(
    "filesystem_levels, summary",
    [
        pytest.param(
            df.LevelsUsedSpace(
                warn_percent=df.Percent(80.0),
                crit_percent=df.Percent(90.0),
                warn_absolute=df.Bytes(800),
                crit_absolute=df.Bytes(900),
                render_as=df.RenderOptions.percent,
            ),
            "(warn/crit at 80.00%/90.00% used)",
            id="Levels configured as percent of used space",
        ),
        pytest.param(
            df.LevelsFreeSpace(
                warn_percent=df.Percent(10.0),
                crit_percent=df.Percent(20.0),
                warn_absolute=df.Bytes(100),
                crit_absolute=df.Bytes(200),
                render_as=df.RenderOptions.percent,
            ),
            "(warn/crit below 10.00%/20.00% free)",
            id="Levels configured as percent of free space",
        ),
        pytest.param(
            df.LevelsUsedSpace(
                warn_percent=df.Percent(80.0),
                crit_percent=df.Percent(90.0),
                warn_absolute=df.Bytes(800),
                crit_absolute=df.Bytes(900),
                render_as=df.RenderOptions.bytes_,
            ),
            "(warn/crit at 800 B/900 B used)",
            id="Levels configured as bytes of used space",
        ),
        pytest.param(
            df.LevelsFreeSpace(
                warn_percent=df.Percent(10.0),
                crit_percent=df.Percent(20.0),
                warn_absolute=df.Bytes(100),
                crit_absolute=df.Bytes(200),
                render_as=df.RenderOptions.bytes_,
            ),
            "(warn/crit below 100 B/200 B free)",
            id="Levels configured as bytes of free space",
        ),
    ],
)
def test__check_summary_text(filesystem_levels: df.FilesystemLevels, summary: str) -> None:
    assert df._check_summary_text(filesystem_levels) == summary
