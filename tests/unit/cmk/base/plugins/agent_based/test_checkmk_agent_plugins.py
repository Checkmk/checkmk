#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import auto, Enum
from typing import Callable, List

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based import checkmk_agent_plugins as cap
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.utils import checkmk

# TODO(sk): Test must be rewritten fully to be based only on the next info
# Input consts: main_dir(os) and sep(os)
# Input fixture: [(filename, plugin|local, subdir|None, VERSION_STRING, VERSION_VALUE),...]
# Calculations: caching(subdir, os), etc


class _OsType(Enum):
    win = auto()
    lnx = auto()


def _main_dir(os_type: _OsType) -> str:
    return (
        "C:\\ProgramData\\checkmk\\agent\\"
        if os_type == _OsType.win
        else "/usr/lib/check_mk_agent/"
    )


def _sep(os_type: _OsType) -> str:
    return "\\" if os_type == _OsType.win else "/"


def _agent_output(os_type: _OsType) -> List[List[str]]:
    main_dir = _main_dir(os_type)
    sep = _sep(os_type)
    return [
        [f"pluginsdir {main_dir}plugins"],
        [f"localdir {main_dir}local"],
        [f'{main_dir}plugins{sep}mk_filestats.py:__version__ = "2.1.0i1"'],  # win skips! this entry
        [f'{main_dir}local{sep}sync_local_check.sh:CMK_VERSION="3.14.15"'],
        [f'{main_dir}plugins{sep}123{sep}zorp:CMK_VERSION = "2.1.0i1"'],  # 123 caching in lnx
        [f'{main_dir}plugins{sep}bad_file:XYZ_VERSION = "2.1.0i1"'],  # invalid entry, to be ignored
    ]


def _section(os_type: _OsType) -> checkmk.PluginSection:
    return checkmk.PluginSection(
        plugins=[
            checkmk.Plugin(
                name,
                "2.1.0i1",
                2010010100,
                123 if os_type == _OsType.lnx and name == "zorp" else None,
            )
            for name in (["mk_filestats.py", "zorp"] if os_type == _OsType.lnx else ["zorp"])
        ],
        local_checks=[
            checkmk.Plugin("sync_local_check.sh", "3.14.15", 3141550000, None),
        ],
    )


@pytest.mark.parametrize(
    "parser,os_type",
    [
        (cap.parse_checkmk_agent_plugins_lnx, _OsType.lnx),
        (cap.parse_checkmk_agent_plugins_win, _OsType.win),
    ],
)
def test_parse_ok_lnx(parser: Callable[[StringTable], checkmk.PluginSection], os_type: _OsType):
    assert parser(_agent_output(os_type)) == _section(os_type)


def test_inventory_lnx() -> None:
    assert list(cap.inventory_checkmk_agent_plugins(_section(_OsType.lnx))) == [
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


def test_inventory_win() -> None:
    assert list(cap.inventory_checkmk_agent_plugins(_section(_OsType.win))) == [
        TableRow(
            path=["software", "applications", "checkmk-agent", "plugins"],
            key_columns={"name": "zorp"},
            inventory_columns={"version": "2.1.0i1", "cache_interval": None},
        ),
        TableRow(
            path=["software", "applications", "checkmk-agent", "local_checks"],
            key_columns={"name": "sync_local_check.sh"},
            inventory_columns={"version": "3.14.15", "cache_interval": None},
        ),
    ]
