#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_secret,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class Params(BaseModel):
    username: str | None = None
    password: tuple[Literal["store", "password"], str] | None = None
    port: int | None = None
    no_cert_check: bool = Field(False, alias="no-cert-check")
    timeout: int | None = None
    log_cutoff_weeks: int | None = Field(None, alias="log-cutoff-weeks")


def commands_function(
    params: Params,
    host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []
    if params.username is not None:
        command_arguments += ["-u", params.username]
    if params.password is not None:
        command_arguments += ["-p", parse_secret(params.password[0], params.password[1])]
    if params.port is not None:
        command_arguments += ["--port", str(params.port)]
    if params.no_cert_check:
        command_arguments.append("--no-cert-check")
    if params.timeout is not None:
        command_arguments += ["--timeout", str(params.timeout)]
    if params.log_cutoff_weeks is not None:
        command_arguments += ["--log-cutoff-weeks", str(params.log_cutoff_weeks)]
    command_arguments.append(host_config.name)
    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_proxmox_ve = SpecialAgentConfig(
    name="proxmox_ve",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
