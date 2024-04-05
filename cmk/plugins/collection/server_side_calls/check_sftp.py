#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    Secret,
)


class Operation(BaseModel):
    local: str
    remote: str


class SFTPParameters(BaseModel):
    host: str
    user: str
    secret: Secret
    description: str | None = None
    port: int | None = None
    timeout: int | None = None
    timestamp: str | None = None
    put: Operation | None = None
    get: Operation | None = None
    look_for_keys: bool = False


def _make_option(name: str, value: str | int | None) -> tuple[str, ...]:
    return () if value is None else (f"--{name}={value}",)


def _commands_check_sftp(
    params: SFTPParameters, host_config: HostConfig, proxies: Mapping[str, HTTPProxy]
) -> Iterable[ActiveCheckCommand]:
    yield ActiveCheckCommand(
        service_description=params.description or f"SFTP {params.host}",
        command_arguments=(
            f"--host={params.host}",
            f"--user={params.user}",
            params.secret.with_format("--secret=%s"),
            *_make_option("port", params.port),
            *_make_option("timeout", params.timeout),
            *_make_option("get-timestamp", params.timestamp),
            *(
                (f"--put-local={params.put.local}", f"--put-remote={params.put.remote}")
                if params.put
                else ()
            ),
            *(
                (f"--get-local={params.get.local}", f"--get-remote={params.get.remote}")
                if params.get
                else ()
            ),
            *(("--look-for-keys",) if params.look_for_keys else ()),
        ),
    )


active_check_sftp = ActiveCheckConfig(
    name="sftp",
    parameter_parser=SFTPParameters.model_validate,
    commands_function=_commands_check_sftp,
)
