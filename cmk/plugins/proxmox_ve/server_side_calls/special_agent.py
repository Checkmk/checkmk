#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class Params(BaseModel):
    username: str | None = None
    password: Secret | None = None
    port: int | None = None
    host: (
        tuple[Literal["host_name"], None]
        | tuple[Literal["ip_address"], None]
        | tuple[Literal["custom"], str]
        | None
    ) = None
    no_cert_check: bool = False
    timeout: int | None = None
    log_cutoff_weeks: int | None = None


def commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    def host_specifier() -> str:
        if params.host and params.host[0] == "host_name":
            return host_config.name
        if params.host and params.host[0] == "ip_address":
            return host_config.primary_ip_config.address
        if params.host and params.host[0] == "custom":
            return replace_macros(params.host[1], host_config.macros)
        return host_config.name or host_config.primary_ip_config.address

    command_arguments: list[str | Secret] = []
    if params.username is not None:
        command_arguments += ["-u", params.username]
    if params.password is not None:
        command_arguments += ["-p", params.password.unsafe()]
    if params.port is not None:
        command_arguments += ["--port", str(params.port)]
    if params.no_cert_check:
        command_arguments.append("--no-cert-check")
    if params.timeout is not None:
        command_arguments += ["--timeout", str(params.timeout)]
    if params.log_cutoff_weeks is not None:
        command_arguments += ["--log-cutoff-weeks", str(params.log_cutoff_weeks)]
    command_arguments.append(host_specifier())
    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_proxmox_ve = SpecialAgentConfig(
    name="proxmox_ve",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
