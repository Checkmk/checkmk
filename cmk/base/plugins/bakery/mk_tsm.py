#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from shlex import quote
from typing import Literal, NotRequired, TypedDict

from cmk.utils.password_store import lookup_for_bakery

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class Auth(TypedDict):
    user: str
    password: tuple[str, str, tuple[str, str]]


class TSMConfig(TypedDict):
    deployment: NotRequired[
        tuple[Literal["sync"], None]
        | tuple[Literal["cached"], float]
        | tuple[Literal["do_not_deploy"], None]
    ]
    auth: NotRequired[Auth]


def get_mk_tsm_files(conf: TSMConfig) -> FileGenerator:
    deployment = conf.get("deployment", ("do_not_deploy", 0.0))
    match deployment:  # type: ignore[exhaustive-match]
        case "do_not_deploy", _:
            return
        case "cached", float(raw_interval):
            interval: int | None = int(raw_interval)
        case "sync", _:
            interval = None

    try:
        auth = conf["auth"]
    except KeyError:
        raise ValueError("Missing 'auth' configuration")

    for base_os in (OS.LINUX, OS.AIX, OS.SOLARIS):
        yield Plugin(base_os=base_os, source=Path("mk_tsm"), interval=interval)  # type: ignore[possibly-undefined]

        yield PluginConfig(
            base_os=base_os,
            lines=_get_mk_tsm_files_config(auth),
            target=Path("tsm.cfg"),
            include_header=True,
        )


def _get_mk_tsm_files_config(auth: Auth) -> list[str]:
    match auth["password"]:
        case _marker, "explicit_password", (_uuid, secret):
            ...
        case _marker, "stored_password", (pwd_id, str()):
            secret = lookup_for_bakery(pwd_id)
        case other:
            raise ValueError(f"Invalid password type: {other!r}")

    return [
        "# Credentials for dsmadmc:",
        f"TSM_USER={quote(auth['user'])}",
        f"TSM_PASSWORD={quote(secret)}",
    ]


register.bakery_plugin(
    name="mk_tsm",
    files_function=get_mk_tsm_files,
)
