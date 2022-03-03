#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import checkmk_agent_plugins as cap
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, TableRow
from cmk.base.plugins.agent_based.checkmk_agent import check_checkmk_agent
from cmk.base.plugins.agent_based.utils import checkmk

_OUTPUT = [
    ["pluginsdir /usr/lib/check_mk_agent/plugins"],
    ["localdir /usr/lib/check_mk_agent/local"],
    ['/usr/lib/check_mk_agent/plugins/mk_filestats.py:__version__ = "2.1.0i1"'],
    ['/usr/lib/check_mk_agent/local/sync_local_check.sh:CMK_VERSION="3.14.15"'],
    ['/usr/lib/check_mk_agent/plugins/123/zorp:CMK_VERSION="2.1.0i1"'],
]


_SECTION = checkmk.PluginSection(
    plugins=[
        checkmk.Plugin("mk_filestats.py", "2.1.0i1", 2010010100, None),
        checkmk.Plugin("zorp", "2.1.0i1", 2010010100, 123),
    ],
    local_checks=[
        checkmk.Plugin("sync_local_check.sh", "3.14.15", 3141550000, None),
    ],
)


def test_parse_ok():
    assert cap.parse_checkmk_agent_plugins_lnx(_OUTPUT) == _SECTION


def test_check():
    assert list(
        check_checkmk_agent(
            {
                "min_versions": ("2.3.0", "1.2.0"),
                "exclude_pattern": "file",
            },
            None,
            _SECTION,
        )
    ) == [
        Result(state=State.OK, summary="Agent plugins: 2"),
        Result(state=State.OK, summary="Local checks: 1"),
        # mk_filestats excluded
        Result(
            state=State.WARN,
            summary="Agent plugin 'zorp': 2.1.0i1 (warn/crit below 2.3.0/1.2.0)",
        ),
        # sync_local_check is OK
    ]


def test_inventory() -> None:
    assert list(cap.inventory_checkmk_agent_plugins(_SECTION)) == [
        TableRow(
            path=["software", "applications", "checkmk-agent", "plugins"],
            key_columns={"name": "mk_filestats.py"},
            inventory_columns={"version": "2.1.0i1", "cache_interval": None},
        ),
        TableRow(
            path=["software", "applications", "checkmk-agent", "plugins"],
            key_columns={"name": "zorp"},
            inventory_columns={"version": "2.1.0i1", "cache_interval": 123},
        ),
        TableRow(
            path=["software", "applications", "checkmk-agent", "local_checks"],
            key_columns={"name": "sync_local_check.sh"},
            inventory_columns={"version": "3.14.15", "cache_interval": None},
        ),
    ]
