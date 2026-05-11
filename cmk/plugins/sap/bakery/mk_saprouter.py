#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, OS, Plugin, PluginConfig


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    user: str = ""
    path: str = ""


def get_mk_saprouter_files(conf: _Config) -> Iterable[Plugin | PluginConfig]:
    if conf.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("mk_saprouter"),
        interval=conf.deployment[1],
    )

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_get_mk_saprouter_config(conf),
        target=Path("saprouter.cfg"),
        include_header=True,
    )


def _get_mk_saprouter_config(config: _Config) -> list[str]:
    return [
        "SAPROUTER_USER=%s" % quote(config.user),
        "SAPGENPSE_PATH=%s" % quote(config.path),
    ]


bakery_plugin_mk_saprouter = BakeryPlugin(
    name="mk_saprouter",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_mk_saprouter_files,
)
