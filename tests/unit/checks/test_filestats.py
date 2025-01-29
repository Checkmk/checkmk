#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, Metric, Result, State


@pytest.mark.parametrize(
    "item,params,data,expected_result",
    [
        pytest.param(
            "TMP",
            {},
            {
                "TMP": (
                    "file_stats",
                    [
                        {
                            "type": "file",
                            "path": "/tmp/file1",
                            "stat_status": "ok",
                            "size": 0,
                            "age": 27465,
                            "mtime": 1679899746,
                        },
                        {
                            "type": "file",
                            "path": "/tmp/file2",
                            "stat_status": "file vanished",
                            "size": None,
                            "age": None,
                            "mtime": None,
                        },
                        {"type": "summary", "count": 5},
                    ],
                )
            },
            [
                Result(state=State.OK, summary="Files in total: 5"),
                Metric("file_count", 5.0),
                Result(state=State.OK, summary="Smallest: 0 B"),
                Result(state=State.OK, summary="Largest: 0 B"),
                Result(state=State.OK, summary="Newest: 7 hours 37 minutes"),
                Result(state=State.OK, summary="Oldest: 7 hours 37 minutes"),
            ],
            id="file without metrics, don't show files",
        ),
        pytest.param(
            "TMP",
            {"minsize_largest": (512, 0), "mincount": (5, 0), "show_all_files": True},
            {
                "TMP": (
                    "file_stats",
                    [
                        {
                            "type": "file",
                            "path": "/tmp/file1",
                            "stat_status": "ok",
                            "size": 0,
                            "age": 27465,
                            "mtime": 1679899746,
                        },
                        {
                            "type": "file",
                            "path": "/tmp/file2",
                            "stat_status": "file vanished",
                            "size": None,
                            "age": None,
                            "mtime": None,
                        },
                        {"type": "summary", "count": 5},
                    ],
                )
            },
            [
                Result(state=State.OK, summary="Files in total: 5"),
                Metric("file_count", 5.0),
                Result(state=State.OK, summary="Smallest: 0 B"),
                Result(state=State.WARN, summary="Largest: 0 B (warn/crit below 512 B/0 B)"),
                Result(state=State.OK, summary="Newest: 7 hours 37 minutes"),
                Result(state=State.OK, summary="Oldest: 7 hours 37 minutes"),
                Result(
                    state=State.OK,
                    summary="1 additional detail available",
                    details="[/tmp/file1] Age: 7 hours 37 minutes, Size: 0 B(!)",
                ),
            ],
            id="file without metrics, show files",
        ),
    ],
)
def test_check_filestats(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    params: Mapping[str, object],
    data: Mapping[str, Sequence[Mapping[str, object]]],
    expected_result: CheckResult,
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("filestats")]
    assert (
        list(check_plugin.check_function(item=item, params=params, section=data)) == expected_result
    )


@pytest.mark.parametrize(
    "item,data,expected_result",
    [
        pytest.param(
            "TMP /tmp/file1",
            {
                "TMP /tmp/file1": (
                    "single_file",
                    [
                        {
                            "type": "file",
                            "path": "/tmp/file1",
                            "stat_status": "ok",
                            "size": 0,
                            "age": 23747,
                            "mtime": 1679899746,
                        }
                    ],
                )
            },
            [
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0.0),
                Result(state=State.OK, summary="Age: 6 hours 35 minutes"),
            ],
            id="file with metrics",
        ),
        pytest.param(
            "TMP /tmp/file2",
            {
                "TMP /tmp/file2": (
                    "single_file",
                    [
                        {
                            "type": "file",
                            "path": "/tmp/file2",
                            "stat_status": "file vanished",
                            "size": None,
                            "age": None,
                            "mtime": None,
                        }
                    ],
                )
            },
            [
                Result(state=State.OK, summary="Status: file vanished"),
            ],
            id="file without metrics",
        ),
    ],
)
def test_check_filestats_single(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    data: Mapping[str, Sequence[Mapping[str, object]]],
    expected_result: CheckResult,
) -> None:
    check_plugin = agent_based_plugins.check_plugins[CheckPluginName("filestats_single")]
    assert list(check_plugin.check_function(item=item, params={}, section=data)) == expected_result
