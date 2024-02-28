#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping
from typing import Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_secret,
    replace_macros,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class CiscoPrimeParams(BaseModel):
    basicauth: tuple[str, tuple[Literal["password", "store"], str]] | None = None
    port: int | None = None
    no_tls: bool = Field(alias="no-tls", default=False)
    no_cert_check: bool = Field(alias="no-cert-check", default=False)
    timeout: int | None = None
    host: str | tuple[str, Mapping[str, str]] | None = None


def generate_cisco_prime_command(
    params: CiscoPrimeParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    if params.host == "host_name":
        host = host_config.name
    elif isinstance(params.host, tuple) and params.host[0] == "custom":
        host = replace_macros(params.host[1]["host"], host_config.macros)
    else:
        if host_config.resolved_address is None:
            raise ValueError(f"IP address for host '{host_config.name}' is not set")
        host = host_config.resolved_address

    yield SpecialAgentCommand(
        command_arguments=[
            elem
            for chunk in (
                ("--hostname", host),
                (
                    "-u",
                    parse_secret(params.basicauth[1], display_format=f"{params.basicauth[0]}:%s"),
                )
                if params.basicauth
                else (),
                ("--port", str(params.port)) if params.port is not None else (),
                ("--no-tls",) if params.no_tls else (),
                ("--no-cert-check",) if params.no_cert_check else (),
                ("--timeout", str(params.timeout)) if params.timeout is not None else (),
            )
            for elem in chunk
        ]
    )


special_agent_cisco_prime = SpecialAgentConfig(
    name="cisco_prime",
    parameter_parser=CiscoPrimeParams.model_validate,
    commands_function=generate_cisco_prime_command,
)
