#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from pathlib import Path
from pprint import pformat
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    instances: tuple[Literal["autodetect", "static"], object] | None = None


def get_nginx_status_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)

    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    yield Plugin(base_os=OS.LINUX, source=Path("nginx_status.py"), interval=interval)

    if config.instances is not None:
        mode, data = config.instances
        yield PluginConfig(
            base_os=OS.LINUX,
            lines=_get_nginx_status_config(mode, data),
            target=Path("nginx_status.cfg"),
            include_header=True,
        )


def _get_nginx_status_config(mode: str, data: object) -> list[str]:
    if mode == "static":
        return ["servers = %s" % pformat(data)]
    return ["ssl_ports = %r" % data]


register.bakery_plugin(
    name="nginx_status",
    files_function=get_nginx_status_files,
)
