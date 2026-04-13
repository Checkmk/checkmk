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
    use_legacy_plugin: bool = False


def get_smart_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    match config.deployment[0]:
        case "do_not_deploy":
            return
        case "sync" | "cached":
            interval = None if (v := config.deployment[1]) is None else int(v)
            source = Path("smart") if config.use_legacy_plugin else Path("smart_posix")
            yield Plugin(base_os=OS.LINUX, source=source, interval=interval)


register.bakery_plugin(
    name="smart",
    files_function=get_smart_files,
)
