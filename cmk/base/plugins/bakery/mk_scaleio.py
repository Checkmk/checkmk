#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import NotRequired, ReadOnly, TypedDict

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register


class ScaleioConfig(TypedDict):
    user: ReadOnly[str]
    password: ReadOnly[password_store.PasswordId]
    interval: NotRequired[ReadOnly[int]]


def get_mk_scaleio_files(conf: ScaleioConfig) -> FileGenerator:
    interval = conf.get("interval", 0)
    if interval <= 60:
        interval = 0
    yield Plugin(base_os=OS.LINUX, source=Path("mk_scaleio"), interval=interval)

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=[
            f"SIO_USER={conf['user']}",
            f"SIO_PASSWORD={password_store.extract(conf['password'])}",
        ],
        target=Path("mk_scaleio.cfg"),
        include_header=True,
    )


register.bakery_plugin(
    name="mk_scaleio",
    files_function=get_mk_scaleio_files,
)
