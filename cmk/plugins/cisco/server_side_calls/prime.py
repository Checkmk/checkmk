#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator
from typing import assert_never, Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class _CiscoPrimeAuth(BaseModel):
    username: str
    password: Secret


class _CustomHost(BaseModel):
    host: str


class CiscoPrimeParams(BaseModel):
    basicauth: _CiscoPrimeAuth | None = None
    port: int | None = None
    no_tls: bool = Field(default=False)
    no_cert_check: bool = Field(default=False)
    timeout: int | None = None
    host: (
        tuple[Literal["ip_address"], None]
        | tuple[Literal["host_name"], None]
        | tuple[Literal["custom"], _CustomHost]
    ) = ("ip_address", None)


def generate_cisco_prime_command(
    params: CiscoPrimeParams, host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    match params.host[1]:
        case None:
            host = (
                host_config.primary_ip_config.address
                if params.host[0] == "ip_address"
                else host_config.name
            )
        case _CustomHost() as custom:
            host = replace_macros(custom.host, host_config.macros)
        case other:
            assert_never(other)

    if params.basicauth:
        auth: tuple[str | Secret, ...] = (
            "-u",
            params.basicauth.password.unsafe(f"{params.basicauth.username}:%s"),
        )
    else:
        auth = ()

    yield SpecialAgentCommand(
        command_arguments=(
            "--hostname",
            host,
            *auth,
            *(("--port", str(params.port)) if params.port is not None else ()),
            *(("--no-tls",) if params.no_tls else ()),
            *(("--no-cert-check",) if params.no_cert_check else ()),
            *(("--timeout", str(params.timeout)) if params.timeout is not None else ()),
        )
    )


special_agent_cisco_prime = SpecialAgentConfig(
    name="cisco_prime",
    parameter_parser=CiscoPrimeParams.model_validate,
    commands_function=generate_cisco_prime_command,
)
