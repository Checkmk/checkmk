#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple, Sequence

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based import network_fs_mounts
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS

NOW_SIMULATED = 581792400, "UTC"


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "%s.delta" % "/ABCshare": [2000000, 30000000],
        "%s.delta" % "/PERFshare": [2000000, 30000000],
        "%s.delta" % "/var/dbaexport": [2000000, 30000000],
        "%s.delta" % "/mnt/test_client": [2000000, 30000000],
    }
    monkeypatch.setattr(network_fs_mounts, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


class SizeBasic(NamedTuple):
    info: Sequence[str]
    text: str


class SizeWithUsage(NamedTuple):
    info: Sequence[str]
    total: int
    used: int
    text: str


size1 = SizeWithUsage(
    ["491520", "460182", "460182", "65536"],
    491520 * 65536,
    491520 * 65536 - 460182 * 65536,
    "6.38% used (1.91 of 30.0 GiB)",
)

size2 = SizeBasic(
    ["201326592", "170803720", "170803720", "32768"],
    "15.16% used (931 GiB of 6.00 TiB)",
)


@pytest.mark.parametrize(
    "string_table, discovery_result",
    [
        ([], []),  # no info
        (  # single mountpoint with data
            [["/ABCshare", "ok", *size1.info]],
            [Service(item="/ABCshare")],
        ),
        (  # two mountpoints with empty data
            [["/AB", "ok", "-", "-", "-", "-"], ["/ABC", "ok", "-", "-", "-", "-"]],
            [Service(item="/AB"), Service(item="/ABC")],
        ),
        (  # Mountpoint with spaces and permission denied
            [["/var/dba", "export", "Permission", "denied"], ["/var/dbaexport", "ok", *size2.info]],
            [Service(item="/var/dba export"), Service(item="/var/dbaexport")],
        ),
        (  # with perfdata
            [["/PERFshare", "ok", *size1.info]],
            [Service(item="/PERFshare")],
        ),
        (  # state == 'hanging'
            [["/test", "hanging", "hanging", "0", "0", "0", "0"]],
            [Service(item="/test hanging")],
        ),
        (  # unknown state
            [["/test", "unknown", "unknown", "1", "1", "1", "1"]],
            [Service(item="/test unknown")],
        ),
        (  # zero block size
            [["/test", "perfdata", "ok", "0", "460182", "460182", "0"]],
            [
                Service(item="/test perfdata"),
            ],
        ),
    ],
)
def test_network_fs_mounts_discovery(
    string_table: StringTable,
    discovery_result: DiscoveryResult,
):
    section = network_fs_mounts.parse_network_fs_mounts(string_table)
    assert list(network_fs_mounts.discover_network_fs_mounts(section)) == discovery_result


@pytest.mark.parametrize(
    "string_table, item, check_result",
    [
        ([], "", []),  # no info
        (  # single mountpoint with data
            [["/ABCshare", "ok", *size1.info]],
            "/ABCshare",
            [
                Result(state=State.OK, summary=size1.text),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -4.37 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -14.55%"),
                Metric(
                    "fs_used",
                    2053767168.0,
                    levels=(25769803776.0, 28991029248.0),
                    boundaries=(0.0, 32212254720.0),
                ),
                Metric("fs_size", 32212254720.0, boundaries=(0.0, None)),
                Metric("fs_growth", -54252.567354853214),
                Metric("fs_trend", -54252.567354853214, boundaries=(0.0, 15534.459259259258)),
            ],
        ),
        (  # two mountpoints with empty data
            [["/AB", "ok", "-", "-", "-", "-"], ["/ABC", "ok", "-", "-", "-", "-"]],
            "/AB",
            [Result(state=State.OK, summary="Mount seems OK")],
        ),
        (
            [["/AB", "ok", "-", "-", "-", "-"], ["/ABC", "ok", "-", "-", "-", "-"]],
            "/ABC",
            [Result(state=State.OK, summary="Mount seems OK")],
        ),
        (  # Mountpoint with spaces and permission denied
            [["/var/dba", "export", "Permission", "denied"], ["/var/dbaexport", "ok", *size2.info]],
            "/var/dba export",
            [Result(state=State.CRIT, summary="State: Permission denied")],
        ),
        (
            [["/var/dba", "export", "Permission", "denied"], ["/var/dbaexport", "ok", *size2.info]],
            "/var/dbaexport",
            [
                Result(state=State.OK, summary=size2.text),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -4.23 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -0.07%"),
                Metric(
                    "fs_used",
                    1000173469696.0,
                    levels=(5277655813324.8, 5937362789990.4),
                    boundaries=(0.0, 6597069766656.0),
                ),
                Metric("fs_size", 6597069766656.0, boundaries=(0.0, None)),
                Metric("fs_growth", -52531.05513336153),
                Metric("fs_trend", -52531.05513336153, boundaries=(0.0, 3181457.256296296)),
            ],
        ),
        (  # with perfdata
            [["/PERFshare", "ok", *size1.info]],
            "/PERFshare",
            [
                Result(state=State.OK, summary=size1.text),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -4.37 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -14.55%"),
                Metric(
                    "fs_used",
                    2053767168.0,
                    levels=(25769803776.0, 28991029248.0),
                    boundaries=(0.0, 32212254720.0),
                ),
                Metric("fs_size", 32212254720.0, boundaries=(0.0, None)),
                Metric("fs_growth", -54252.567354853214),
                Metric("fs_trend", -54252.567354853214, boundaries=(0.0, 15534.459259259258)),
            ],
        ),
        (  # state == 'hanging'
            [["/test", "hanging", "hanging", "0", "0", "0", "0"]],
            "/test hanging",
            [Result(state=State.CRIT, summary="State: Hanging")],
        ),
        (  # unknown state
            [["/test", "unknown", "unknown", "1", "1", "1", "1"]],
            "/test unknown",
            [Result(state=State.CRIT, summary="State: Unknown")],
        ),
        (  # zero block size
            [["/test", "perfdata", "ok", "0", "460182", "460182", "0"]],
            "/test perfdata",
            [Result(state=State.CRIT, summary="Stale fs handle")],
        ),
    ],
)
def test_network_fs_mounts_check(
    string_table: StringTable,
    item: str,
    check_result: CheckResult,
    value_store_patch,
):
    section = network_fs_mounts.parse_network_fs_mounts(string_table)
    with on_time(*NOW_SIMULATED):
        actual_check_results = list(
            network_fs_mounts.check_network_fs_mount(
                item, {**FILESYSTEM_DEFAULT_PARAMS, **{"has_perfdata": True}}, section
            )
        )
    assert [r for r in actual_check_results if isinstance(r, Result)] == [
        r for r in check_result if isinstance(r, Result)
    ]
    for actual_metric, expected_metric in zip(
        [m for m in actual_check_results if isinstance(m, Metric)],
        [m for m in check_result if isinstance(m, Metric)],
    ):
        assert actual_metric.name == expected_metric.name
        assert actual_metric.value == expected_metric.value
        if hasattr(actual_metric, "levels"):
            assert actual_metric.levels[0] == pytest.approx(expected_metric.levels[0])
            assert actual_metric.levels[1] == pytest.approx(expected_metric.levels[1])


@pytest.mark.parametrize(
    "string_table, item, check_result",
    [
        (
            [
                [
                    """
                    {"mountpoint": "/mnt/test_client", "source": "127.0.0.1:/mnt/test", "state": "ok", "usage": {"total_blocks": 237102, "free_blocks_su": 161350, "free_blocks": 149238, "blocksize": 1048576}}
                    """
                ]
            ],
            "/mnt/test_client",
            [
                Result(state=State.OK, summary="Source: 127.0.0.1:/mnt/test"),
                Result(state=State.OK, summary="37.06% used (85.8 of 232 GiB)"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -4.35 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: -1.88%"),
            ],
        ),
    ],
)
def test_nfsmount_v2_check(
    string_table: StringTable,
    item: str,
    check_result: CheckResult,
    value_store_patch,
):
    section = network_fs_mounts.parse_nfsmounts_v2(string_table)
    with on_time(*NOW_SIMULATED):
        assert (
            list(network_fs_mounts.check_network_fs_mount(item, FILESYSTEM_DEFAULT_PARAMS, section))
            == check_result
        )
