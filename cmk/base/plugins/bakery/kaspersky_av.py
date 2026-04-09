#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]


def get_kaspersky_av_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("kaspersky_av"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )


register.bakery_plugin(
    name="kaspersky_av",
    files_function=get_kaspersky_av_files,
)
