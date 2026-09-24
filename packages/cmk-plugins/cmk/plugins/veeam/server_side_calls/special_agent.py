#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

type Connection = tuple[Literal["ip_address", "host_name", "custom_address"], str | None]


class Params(BaseModel):
    connection: Connection
    port: int
    user: str
    password: Secret
    disable_cert_verification: bool


def _connection_address(connection: Connection, host_config: HostConfig) -> str:
    match connection:
        case ("ip_address", _):
            return host_config.primary_ip_config.address
        case ("host_name", _):
            return host_config.name
        case ("custom_address", str(address)):
            return replace_macros(address, host_config.macros)
        case _:
            raise ValueError(f"Invalid connection configuration: {connection!r}")


def _tls_arguments(disable_cert_verification: bool, host_config: HostConfig) -> list[str]:
    if disable_cert_verification:
        return ["--disable-cert-verification"]
    # We may be talking to an IP address while the certificate is issued for a host
    # name, so validation is pinned to the Checkmk host name.
    return ["--cert-server-name", host_config.name]


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = [
        "--user",
        params.user,
        "--password-id",
        params.password,
        "--port",
        str(params.port),
        *_tls_arguments(params.disable_cert_verification, host_config),
        _connection_address(params.connection, host_config),
    ]

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_veeam = SpecialAgentConfig(
    name="veeam",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
