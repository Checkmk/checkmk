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
    java_home: str = ""
    paths: list[str] = []


def get_jar_signature_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("jar_signature"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_get_jar_signature_config_lines(config),
        target=Path("jar_signature.cfg"),
        include_header=True,
    )


def _get_jar_signature_config_lines(config: _Config) -> list[str]:
    return [
        "JAVA_HOME=%s" % quote(config.java_home),
        "JAR_PATH=%s" % quote(" ".join(config.paths)),
    ]


register.bakery_plugin(
    name="jar_signature",
    files_function=get_jar_signature_files,
)
