#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from enum import auto, Enum

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import TableRow
from cmk.ccc.version import parse_check_mk_version
from cmk.plugins.collection.agent_based import checkmk_agent_plugins as cap
from cmk.plugins.lib import checkmk


class _OsType(Enum):
    win = auto()
    lnx = auto()


class _FileKind(Enum):
    plugin = "plugins"
    local = "local_checks"

    def __str__(self):
        return str(self.value)


@dataclass(frozen=True)
class File:
    name: str
    version: str
    kind: _FileKind
    cache_interval: int | None

    def as_table_row(self) -> TableRow:
        return TableRow(
            path=["software", "applications", "checkmk-agent", str(self.kind)],
            key_columns={"name": self.name},
            inventory_columns={"version": self.version, "cache_interval": self.cache_interval},
        )


def _win_file_list() -> list[File]:
    return [
        File(name="zorp", version="2.1.0i1", cache_interval=None, kind=_FileKind.plugin),
        File(
            name="sync_local_check.sh",
            version="3.14.15",
            cache_interval=None,
            kind=_FileKind.local,
        ),
    ]


def _lin_file_list() -> list[File]:
    return [
        File(name="mk_filestats.py", version="2.1.0i1", cache_interval=None, kind=_FileKind.plugin),
        File(name="zorp", version="2.1.0i1", cache_interval=123, kind=_FileKind.plugin),
        File(
            name="sync_local_check.sh",
            version="3.14.15",
            cache_interval=None,
            kind=_FileKind.local,
        ),
    ]


def _file_list(os_type: _OsType) -> list[File]:
    match os_type:
        case _OsType.win:
            return _win_file_list()
        case _OsType.lnx:
            return _lin_file_list()

    # the only way to satisfy pylint, which is not smart enough to support match correctly
    return []


def _main_dir(os_type: _OsType) -> str:
    return (
        "C:\\ProgramData\\checkmk\\agent\\"
        if os_type == _OsType.win
        else "/usr/lib/check_mk_agent/"
    )


@dataclass(frozen=True)
class _AgentRow:
    dir: str
    name: str
    ver: str
    cache: str


def _produce_agent_output(os_type: _OsType) -> list[list[str]]:
    main_dir = _main_dir(os_type)
    sep = "\\" if os_type == _OsType.win else "/"
    rows = [
        _AgentRow(
            dir="plugins" if f.kind == _FileKind.plugin else "local",
            name=f.name,
            ver=f.version,
            cache="" if f.cache_interval is None else f"{f.cache_interval}{sep}",
        )
        for f in _lin_file_list()
    ]
    plugin_rows = [
        [f"{main_dir}{rows[i].dir}{sep}{rows[i].cache}{rows[i].name}{marker}{rows[i].ver}"]
        for i, marker in zip([0, 2, 1], [":__version__ = ", ":CMK_VERSION=", ":CMK_VERSION = "])
    ]
    return [
        [f"pluginsdir {main_dir}plugins"],
        [f"localdir {main_dir}local"],
        *plugin_rows,
        [f'{main_dir}plugins{sep}bad_file:XYZ_VERSION = "2.1.0i1"'],
    ]


def _get_parser(os_type: _OsType) -> Callable[[StringTable], checkmk.PluginSection]:
    return (
        cap.parse_checkmk_agent_plugins_lnx
        if os_type == _OsType.lnx
        else cap.parse_checkmk_agent_plugins_win
    )


def _produce_plugin_section(os_type: _OsType) -> checkmk.PluginSection:
    parser = _get_parser(os_type)
    return parser(_produce_agent_output(os_type))


def _expected_section(files: list[File]) -> checkmk.PluginSection:
    return checkmk.PluginSection(
        plugins=[
            checkmk.Plugin(
                f.name,
                f.version,
                parse_check_mk_version(f.version),
                f.cache_interval,
            )
            for f in files
            if f.kind == _FileKind.plugin
        ],
        local_checks=[
            checkmk.Plugin(
                f.name,
                f.version,
                parse_check_mk_version(f.version),
                f.cache_interval,
            )
            for f in files
            if f.kind == _FileKind.local
        ],
    )


@pytest.mark.parametrize("os_type", [_OsType.lnx, _OsType.win])
def test_parse_ok(os_type: _OsType) -> None:
    assert _produce_plugin_section(os_type) == _expected_section(_file_list(os_type))


@pytest.mark.parametrize("os_type", [_OsType.lnx, _OsType.win])
def test_inventory(os_type: _OsType) -> None:
    expected_inventory = [f.as_table_row() for f in _file_list(os_type)]
    obtained_inventory = list(cap.inventory_checkmk_agent_plugins(_produce_plugin_section(os_type)))
    assert obtained_inventory == expected_inventory
