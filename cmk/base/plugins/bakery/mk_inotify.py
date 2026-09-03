#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Folder(BaseModel):
    path: str
    operations: Sequence[str]


class _Files(BaseModel):
    path: str
    files: Sequence[str]
    operations: Sequence[str]


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync"], None]
    heartbeat_timeout: float = 120.0
    write_interval: float = 10.0
    max_messages_per_interval: int = 100
    stats_retention: float = 120.0
    entries: Sequence[tuple[Literal["folder"], _Folder] | tuple[Literal["files"], _Files]] = ()


def get_mk_inotify_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(base_os=OS.LINUX, source=Path("mk_inotify.py"))

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_inotify_config(config)),
        target=Path("mk_inotify.cfg"),
        include_header=True,
    )


def _get_mk_inotify_config(config: _Config) -> Iterator[str]:
    yield from [
        "[global]",
        f"heartbeat_timeout={int(config.heartbeat_timeout)}",
        f"write_interval={int(config.write_interval)}",
        f"max_messages_per_interval={config.max_messages_per_interval}",
        f"stats_retention={int(config.stats_retention)}",
        "",
    ]

    for _kind, entry in config.entries:
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
