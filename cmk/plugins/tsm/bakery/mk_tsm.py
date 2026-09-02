#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, OS, Plugin, PluginConfig, Secret


class _Auth(BaseModel):
    user: str
    password: Secret


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None] = (
        "do_not_deploy",
        None,
    )
    auth: _Auth | None = None


def get_mk_tsm_files(conf: _Config) -> Iterator[Plugin | PluginConfig]:
    if conf.deployment[0] == "do_not_deploy":
        return

    if conf.auth is None:
        raise ValueError("Missing 'auth' configuration")

    for base_os in (OS.LINUX, OS.AIX, OS.SOLARIS):
        yield Plugin(base_os=base_os, source=Path("mk_tsm"), interval=conf.deployment[1])
        yield PluginConfig(
            base_os=base_os,
            lines=_get_mk_tsm_config(conf.auth),
            target=Path("tsm.cfg"),
            include_header=True,
        )


def _get_mk_tsm_config(auth: _Auth) -> list[str]:
    return [
        "# Credentials for dsmadmc:",
        f"TSM_USER={quote(auth.user)}",
        f"TSM_PASSWORD={quote(auth.password.revealed)}",
    ]


bakery_plugin_mk_tsm = BakeryPlugin(
    name="mk_tsm",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_mk_tsm_files,
)
