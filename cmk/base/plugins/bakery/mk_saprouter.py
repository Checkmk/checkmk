#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    user: str = ""
    path: str = ""


def get_mk_saprouter_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    yield Plugin(base_os=OS.LINUX, source=Path("mk_saprouter"), interval=interval)

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_get_mk_saprouter_config(config),
        target=Path("saprouter.cfg"),
        include_header=True,
    )


def _get_mk_saprouter_config(config: _Config) -> list[str]:
    return [
        "SAPROUTER_USER=%s" % quote(config.user),
        "SAPGENPSE_PATH=%s" % quote(config.path),
    ]


register.bakery_plugin(
    name="mk_saprouter",
    files_function=get_mk_saprouter_files,
)
