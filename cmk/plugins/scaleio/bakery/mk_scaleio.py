#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, FileGenerator, OS, Plugin, PluginConfig, Secret


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    user: str = ""
    password: Secret | None = None


def get_mk_scaleio_files(config: _Config) -> FileGenerator:
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("mk_scaleio"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=[
            f"SIO_USER={config.user}",
            f"SIO_PASSWORD={'' if config.password is None else config.password.revealed}",
        ],
        target=Path("mk_scaleio.cfg"),
        include_header=True,
    )


bakery_plugin_mk_scaleio = BakeryPlugin(
    name="mk_scaleio",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_mk_scaleio_files,
)
