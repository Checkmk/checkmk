#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult


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
                Result(state=State.OK, summary="Smallest: 0.00 B"),
                Result(state=State.OK, summary="Largest: 0.00 B"),
                Result(state=State.OK, summary="Newest: 7 h"),
                Result(state=State.OK, summary="Oldest: 7 h"),
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
                Result(state=State.OK, summary="Smallest: 0.00 B"),
                Result(
                    state=State.WARN, summary="Largest: 0.00 B (warn/crit below 512.00 B/0.00 B)"
                ),
                Result(state=State.OK, summary="Newest: 7 h"),
                Result(state=State.OK, summary="Oldest: 7 h"),
                Result(
                    state=State.OK,
                    summary="1 additional detail available",
                    details="[/tmp/file1] Age: 7 h, Size: 0.00 B(!)",
                ),
            ],
            id="file without metrics, show files",
        ),
    ],
)
def test_check_filestats(
    fix_register: FixRegister,
    item: str,
    params: Mapping[str, object],
    data: Mapping[str, Sequence[Mapping[str, object]]],
    expected_result: CheckResult,
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("filestats")]
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
                Result(state=State.OK, summary="Size: 0.00 B"),
                Metric("size", 0.0),
                Result(state=State.OK, summary="Age: 6 h"),
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
    fix_register: FixRegister,
    item: str,
    data: Mapping[str, Sequence[Mapping[str, object]]],
    expected_result: CheckResult,
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("filestats_single")]
    assert list(check_plugin.check_function(item=item, params={}, section=data)) == expected_result
