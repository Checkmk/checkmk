#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    hostnames: Sequence[str] = ()


def get_dnsclient_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    for o_s in (OS.LINUX, OS.SOLARIS, OS.AIX):
        yield Plugin(base_os=o_s, source=Path("dnsclient"), interval=interval)

    if config.hostnames:
        for o_s in (OS.LINUX, OS.SOLARIS, OS.AIX):
            yield PluginConfig(
                base_os=o_s,
                lines=_get_dnsclient_config_lines(config.hostnames),
                target=Path("dnsclient.cfg"),
                include_header=True,
            )


def _get_dnsclient_config_lines(hostnames: Sequence[str]) -> list[str]:
    return [
        "# Hostnames to test resolver with",
        "HOSTADDRESSES=%s" % quote(" ".join(hostnames)),
    ]


register.bakery_plugin(
    name="dnsclient",
    files_function=get_dnsclient_files,
)
