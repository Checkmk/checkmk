#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register


class _Config(BaseModel):
    user: str
    password: password_store.PasswordId
    interval: int = 0


def get_mk_scaleio_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    interval = config.interval
    if interval <= 60:
        interval = 0
    yield Plugin(base_os=OS.LINUX, source=Path("mk_scaleio"), interval=interval)

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=[
            f"SIO_USER={config.user}",
            f"SIO_PASSWORD={password_store.extract(config.password)}",
        ],
        target=Path("mk_scaleio.cfg"),
        include_header=True,
    )


register.bakery_plugin(
    name="mk_scaleio",
    files_function=get_mk_scaleio_files,
)
