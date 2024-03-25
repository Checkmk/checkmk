#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class _CiscoPrimeAuth(BaseModel):
    username: str
    password: Secret


class CiscoPrimeParams(BaseModel):
    basicauth: _CiscoPrimeAuth | None = None
    port: int | None = None
    no_tls: bool = Field(default=False)
    no_cert_check: bool = Field(default=False)
    timeout: int | None = None
    host: str | tuple[str, Mapping[str, str]] | None = None


def generate_cisco_prime_command(
    params: CiscoPrimeParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    match params.host:
        case "host_name":
            host = host_config.name
        case ("custom", {"host": str(custom_host_name)}):
            host = replace_macros(custom_host_name, host_config.macros)
        case _:
            host = host_config.primary_ip_config.address

    if params.basicauth:
        auth: tuple[str | Secret, ...] = (
            "-u",
            params.basicauth.password.with_format(f"{params.basicauth.username}:%s"),
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
