#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, OS, Plugin


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]


def get_plesk_files(conf: _Config) -> Iterable[Plugin]:
    if conf.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("plesk_backups.py"),
        interval=conf.deployment[1],
    )
    yield Plugin(base_os=OS.LINUX, source=Path("plesk_domains.py"))


bakery_plugin_plesk = BakeryPlugin(
    name="plesk",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_plesk_files,
)
