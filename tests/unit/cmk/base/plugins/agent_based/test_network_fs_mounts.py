#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple, Sequence

import pytest

from tests.testlib import on_time

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.item_state
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS

check_name = "nfsmounts"

NOW_SIMULATED = 581792400, "UTC"


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "df.%s.delta" % "/ABCshare": [2000000, 30000000],
        "df.%s.delta" % "/PERFshare": [2000000, 30000000],
        "df.%s.delta" % "/var/dbaexport": [2000000, 30000000],
    }
    monkeypatch.setattr(cmk.base.item_state, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name="discover_network_fs_mounts")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name="check_network_fs_mount")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name="parse_network_fs_mounts")
def _get_parse(fix_register):
    return fix_register.agent_sections[SectionName(check_name)].parse_function


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
    "6.38% used (1.91 of 30.00 GB), trend: 0.00 B / 24 hours",
)

size2 = SizeBasic(
    ["201326592", "170803720", "170803720", "32768"],
    "15.16% used (931.48 GB of 6.00 TB), trend: 0.00 B / 24 hours",
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
    parse_network_fs_mounts,
    discover_network_fs_mounts,
):
    section = parse_network_fs_mounts(string_table)
    assert list(discover_network_fs_mounts(section)) == discovery_result


@pytest.mark.parametrize(
    "string_table, item, check_result",
    [
        ([], "", []),  # no info
        (  # single mountpoint with data
            [["/ABCshare", "ok", *size1.info]],
            "/ABCshare",
            [
                Result(state=State.OK, summary=size1.text),
                Metric(
                    "fs_used",
                    2053767168.0,
                    levels=(25769803776.0, 28991029248.0),
                    boundaries=(0.0, 32212254720.0),
                ),
                Metric("fs_size", 32212254720.0),
                Metric("fs_growth", -54252.567354853214),
                Metric("fs_trend", 0.0, boundaries=(0.0, 15534.459259259258)),
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
            [Result(state=State.CRIT, summary="Permission denied")],
        ),
        (
            [["/var/dba", "export", "Permission", "denied"], ["/var/dbaexport", "ok", *size2.info]],
            "/var/dbaexport",
            [
                Result(state=State.OK, summary=size2.text),
                Metric(
                    "fs_used",
                    1000173469696.0,
                    levels=(5277655813324.8, 5937362789990.4),
                    boundaries=(0.0, 6597069766656.0),
                ),
                Metric("fs_size", 6597069766656.0),
                Metric("fs_growth", -52531.05513336153),
                Metric("fs_trend", 0.0, boundaries=(0.0, 3181457.256296296)),
            ],
        ),
        (  # with perfdata
            [["/PERFshare", "ok", *size1.info]],
            "/PERFshare",
            [
                Result(state=State.OK, summary=size1.text),
                Metric(
                    "fs_used",
                    2053767168.0,
                    levels=(25769803776.0, 28991029248.0),
                    boundaries=(0.0, 32212254720.0),
                ),
                Metric("fs_size", 32212254720.0),
                Metric("fs_growth", -54252.567354853214),
                Metric("fs_trend", 0.0, boundaries=(0.0, 15534.459259259258)),
            ],
        ),
        (  # state == 'hanging'
            [["/test", "hanging", "hanging", "0", "0", "0", "0"]],
            "/test hanging",
            [Result(state=State.CRIT, summary="Server not responding")],
        ),
        (  # unknown state
            [["/test", "unknown", "unknown", "1", "1", "1", "1"]],
            "/test unknown",
            [Result(state=State.CRIT, summary="Unknown state: unknown")],
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
    parse_network_fs_mounts,
    check_network_fs_mount,
    value_store_patch,
):
    section = parse_network_fs_mounts(string_table)
    with on_time(*NOW_SIMULATED):
        assert (
            list(
                check_network_fs_mount(
                    item, {**FILESYSTEM_DEFAULT_LEVELS, **{"has_perfdata": True}}, section
                )
            )
            == check_result
        )
