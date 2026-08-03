#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from pathlib import Path
from typing import Any

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register


def get_mk_scaleio_files(conf: dict[str, Any]) -> FileGenerator:
    interval = conf.get("interval", 0)
    if interval <= 60:
        interval = 0
    yield Plugin(base_os=OS.LINUX, source=Path("mk_scaleio"), interval=interval)

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_get_mk_scaleio_config(conf),
        target=Path("mk_scaleio.cfg"),
        include_header=True,
    )


def _get_mk_scaleio_config(conf: dict[str, Any]) -> list[str]:
    return [
        "SIO_USER=%s" % conf["user"],
        "SIO_PASSWORD=%s" % password_store.extract(conf["password"]),
    ]


register.bakery_plugin(
    name="mk_scaleio",
    files_function=get_mk_scaleio_files,
)
