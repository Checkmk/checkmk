#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    parse_secret,
    Secret,
)


class Params(BaseModel):
    share: str
    host: Literal["use_parent_host"] | tuple[Literal["define_host"], str]
    levels: tuple[float, float]
    workgroup: str | None = None
    port: int | None = None
    auth: tuple[str, tuple[Literal["password", "store"], str]] | None = None
    ip_address: str | None = None


def check_disk_smb_arguments(
    params: Params, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    def _get_address(host_config: HostConfig, params: Params) -> str:
        if params.host != "use_parent_host":
            return params.host[1]

        if host_config.address:
            return host_config.address

        raise ValueError("No IP address available")

    args: list[str | Secret] = [
        params.share,
        "-H",
        _get_address(host_config, params),
    ]

    warn, crit = params.levels
    args += ["--levels", str(warn), str(crit)]

    if params.workgroup is not None:
        args += ["-W", params.workgroup]

    if params.port is not None:
        args += ["-P", str(params.port)]

    if params.auth is not None:
        username, pw = params.auth
        args += [
            "-u",
            username,
            "-p",
            parse_secret(pw[0], pw[1]),
        ]

    if params.ip_address is not None:
        args += ["-a", params.ip_address]

    yield ActiveCheckCommand(
        service_description="SMB Share " + params.share.replace("$", ""),
        command_arguments=args,
    )


active_check_config = ActiveCheckConfig(
    name="disk_smb",
    parameter_parser=Params.model_validate,
    commands_function=check_disk_smb_arguments,
)
