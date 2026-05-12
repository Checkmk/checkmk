#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from pathlib import Path
from pprint import pformat
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, OS, Plugin, PluginConfig


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    instances: tuple[Literal["autodetect", "static"], object] | None = None


def get_apache_status_files(conf: _Config) -> Iterable[Plugin | PluginConfig]:
    if conf.deployment[0] == "do_not_deploy":
        return

    yield Plugin(base_os=OS.LINUX, source=Path("apache_status.py"), interval=conf.deployment[1])

    if conf.instances is not None:
        mode, data = conf.instances
        yield PluginConfig(
            base_os=OS.LINUX,
            lines=_get_apache_status_config(mode, data),
            target=Path("apache_status.cfg"),
            include_header=True,
        )


def _get_apache_status_config(mode: str, data: object) -> list[str]:
    if mode == "static":
        return ["servers = %s" % pformat(data)]
    return [f"ssl_ports = {data!r}"]


bakery_plugin_apache_status = BakeryPlugin(
    name="apache_status",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_apache_status_files,
)
