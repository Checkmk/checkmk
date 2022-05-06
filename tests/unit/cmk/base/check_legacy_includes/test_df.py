#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Sequence

import pytest
from pytest_mock import MockerFixture

from cmk.base.check_legacy_includes.df import df_check_filesystem_single_coroutine
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS


@pytest.mark.parametrize(
    ["data", "expected_result"],
    [
        pytest.param(
            (
                0,
                None,
                None,
                None,
                None,
            ),
            [
                (
                    1,
                    "Size of filesystem is 0 MB",
                    [],
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
                (
                    0,
                    "42.71% used (42.81 of 100.25 GB)",
                    [
                        ("fs_used", 43841, 82124.0, 92389.5, 0, 102655),
                        ("fs_size", 102655),
                        ("fs_used_percent", 42.707125809751105),
                    ],
                ),
                (
                    0,
                    "trend: 0.00 B / 24 hours",
                    [
                        ("growth", 161105947.82608697),
                        ("trend", 0.0, None, None, 0, 4277.291666666667),
                    ],
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
                (
                    0,
                    "42.71% used (42.81 of 100.25 GB)",
                    [
                        ("fs_used", 43841, 82124.0, 92389.5, 0, 102655),
                        ("fs_size", 102655),
                        ("fs_used_percent", 42.707125809751105),
                    ],
                ),
                (
                    0,
                    "trend: 0.00 B / 24 hours",
                    [
                        ("growth", 161105947.82608697),
                        ("trend", 0.0, None, None, 0, 4277.291666666667),
                    ],
                ),
                (
                    2,
                    "Inodes used: 99.83% (warn/crit at 90.00%/95.00%), Inodes available: 111 "
                    "(0.17%)",
                    [("inodes_used", 65375.0, 58937.4, 62211.7, 0.0, 65486.0)],
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
                (
                    0,
                    "42.71% used (42.81 of 100.25 GB)",
                    [
                        ("fs_used", 43841, 82124.0, 92389.5, 0, 102655),
                        ("fs_size", 102655),
                        ("fs_used_percent", 42.707125809751105),
                    ],
                ),
                (
                    0,
                    "trend: 0.00 B / 24 hours",
                    [
                        ("growth", 161105947.82608697),
                        ("trend", 0.0, None, None, 0, 4277.291666666667),
                    ],
                ),
                # Bug, there should be an inode result here
            ],
            id="zero inodes left",
        ),
    ],
)
def test_df_check_filesystem_single_coroutine(
    mocker: MockerFixture,
    data: tuple[
        Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]
    ],
    expected_result: Sequence[tuple[int, str, Sequence[tuple]]],
) -> None:
    mocker.patch(
        "cmk.base.item_state.get_value_store",
        return_value={"df./fake.delta": (100, 954)},
    )
    assert (
        list(
            df_check_filesystem_single_coroutine(
                "/fake",
                *data,
                FILESYSTEM_DEFAULT_LEVELS,
                this_time=123,
            )
        )
        == expected_result
    )
