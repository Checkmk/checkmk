#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Folder(NamedTuple):
    path: str
    operations: Sequence[str]


class _Files(NamedTuple):
    path: str
    files: Sequence[str]
    operations: Sequence[str]


_RawEntry = tuple[str, Sequence[str]] | tuple[str, Sequence[str], Sequence[str]]
_RawConfig = tuple[float, float, int, float, Sequence[_RawEntry]]


def _parse_entry(entry: _RawEntry) -> _Folder | _Files:
    match entry:
        case (path, operations):
            return _Folder(path, operations)
        case (path, files, operations):
            return _Files(path, files, operations)


def get_mk_inotify_files(conf: _RawConfig) -> FileGenerator:
    yield Plugin(base_os=OS.LINUX, source=Path("mk_inotify.py"))

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_inotify_config(conf)),
        target=Path("mk_inotify.cfg"),
        include_header=True,
    )


def _get_mk_inotify_config(conf: _RawConfig) -> Iterator[str]:
    heartbeat_timeout, write_interval, max_messages_per_interval, stats_retention, entries = conf

    yield from [
        "[global]",
        f"heartbeat_timeout={int(heartbeat_timeout)}",
        f"write_interval={int(write_interval)}",
        f"max_messages_per_interval={int(max_messages_per_interval)}",
        f"stats_retention={int(stats_retention)}",
        "",
    ]

    for entry in map(_parse_entry, entries):
        match entry:
            case _Folder():
                yield f"[{entry.path}]"
            case _Files():
                yield "[{}|{}]".format(entry.path, "|".join(entry.files))
        for operation in entry.operations:
            yield f"{operation}=1"


register.bakery_plugin(
    name="mk_inotify",
    files_function=get_mk_inotify_files,
)
