#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register

_Auth = Literal["system"] | tuple[Literal["db"], tuple[str, str]]


class _Config(BaseModel):
    auth_default: _Auth = "system"
    auth_instances: Sequence[tuple[str, _Auth]] = ()
    inst_excludes: Sequence[str] = ()
    timeout_connection: int | None = None
    timeout_command: int | None = None


def get_mssql_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)

    yield Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs"))

    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=list(
            _get_mssql_ini_lines(config.auth_default, config, excludes=config.inst_excludes)
        ),
        target=Path("mssql.ini"),
    )

    for instance, auth in config.auth_instances:
        sane_id = _sanitize_instance_for_filename(instance)
        yield PluginConfig(
            base_os=OS.WINDOWS,
            lines=list(_get_mssql_ini_lines(auth, config)),
            target=Path(f"mssql_{sane_id}.ini"),
        )


def _get_mssql_ini_lines(
    auth: _Auth,
    config: _Config,
    excludes: Sequence[str] = (),
) -> Iterator[str]:
    yield "[auth]"
    match auth:
        case "system":
            yield "type = system"
        case ("db", (user, password)):
            yield "type = db"
            yield f"username = {user}"
            yield f"password = {password}"

    if excludes:
        yield "[instance]"
        yield "exclude = %s" % ",".join(excludes)

    yield "[timeouts]"
    if config.timeout_connection is not None:
        yield f"timeout_connection = {config.timeout_connection}"
    if config.timeout_command is not None:
        yield f"timeout_command = {config.timeout_command}"


def _sanitize_instance_for_filename(instance: str) -> str:
    # we can't have backslashes. Make sure this function
    # is mirrored in mssql.vbs!
    return instance.replace("\\", "_").replace(",", "_")


register.bakery_plugin(
    name="mssql",
    files_function=get_mssql_files,
)
