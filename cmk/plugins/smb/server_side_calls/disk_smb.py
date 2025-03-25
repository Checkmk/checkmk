#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
    Secret,
)


class Auth(BaseModel):
    user: str
    password: Secret


class Params(BaseModel):
    share: str
    workgroup: str | None = None
    host: tuple[Literal["use_parent_host", "define_host"], str]
    ip_address: str | None = None
    port: int | None = None
    levels: tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]
    auth: Auth | None = None


def _get_address(host_config: HostConfig, params: Params) -> str:
    match params.host:
        case ("use_parent_host", _unused):
            return host_config.primary_ip_config.address
        case ("define_host", str(host)):
            return replace_macros(host, host_config.macros)
        case other:
            raise ValueError(other)


def commands_check_disk_smb(
    params: Params, host_config: HostConfig
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = [
        replace_macros(params.share, host_config.macros),
        "-H",
        _get_address(host_config, params),
    ]

    match params.levels:
        case ("no_levels", None):
            pass
        case ("fixed", (warn, crit)):
            args += ["--levels", str(warn), str(crit)]

    if params.workgroup is not None:
        args += ["-W", replace_macros(params.workgroup, host_config.macros)]

    if params.port is not None:
        args += ["--port", str(params.port)]

    if params.auth is not None:
        args += ["-u", params.auth.user, "--password-reference", params.auth.password]

    if params.ip_address is not None:
        args += ["-a", replace_macros(params.ip_address, host_config.macros)]

    yield ActiveCheckCommand(
        service_description="SMB Share " + params.share.replace("$", ""),
        command_arguments=args,
    )


active_check_config = ActiveCheckConfig(
    name="disk_smb",
    parameter_parser=Params.model_validate,
    commands_function=commands_check_disk_smb,
)
