#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.plugins.bazel.agent_based.bazel_cache_status as bcs
from cmk.agent_based.v2 import Metric, Result, Service, State


@pytest.fixture(scope="module", name="section")
def _section() -> bcs.Section:
    return bcs.parse_bazel_cache_status(
        [
            [
                '{"curr_size": 283044515840, "git_commit": "c5bf6e13938aa89923c637b5a4f01c2203a3c9f8", "max_size": 483183820800, "num_files": 15922442, "num_goroutines": 9, "reserved_size": 0, "server_time": 1714051616, "uncompressed_size": 666901065728}'
            ]
        ]
    )


def test_discover_bazel_cache_status(section: bcs.Section) -> None:
    assert list(bcs.discover_bazel_cache_status(section)) == [Service()]


def test_check_bazel_cache_status(section: bcs.Section) -> None:
    assert list(bcs.check_bazel_cache_status(section)) == [
        Result(state=State.OK, summary="Bazel Cache Status is OK"),
        Result(state=State.OK, summary="Current size: 264 GiB"),
        Metric("bazel_cache_status_curr_size", 283044515840.0),
        Result(state=State.OK, summary="Maximum size: 450 GiB"),
        Metric("bazel_cache_status_max_size", 483183820800.0),
        Result(state=State.OK, summary="Number of files: 15922442"),
        Metric("bazel_cache_status_num_files", 15922442.0),
        Result(state=State.OK, summary="Number of Go routines: 9"),
        Metric("bazel_cache_status_num_goroutines", 9.0),
        Result(state=State.OK, summary="Reserved size: 0 B"),
        Metric("bazel_cache_status_reserved_size", 0.0),
        Result(state=State.OK, summary="Uncompressed size: 621 GiB"),
        Metric("bazel_cache_status_uncompressed_size", 666901065728.0),
    ]
