#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)


class Params(BaseModel, frozen=True):
    description: str | None = None
    port: int | None = Field(None, ge=0, le=65535)
    timeout: int | None = None
    remote_version: str | None = None
    remote_protocol: str | None = None


def commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    command_arguments = ["-H", host_config.primary_ip_config.address]

    if params.timeout is not None:
        command_arguments += ["-t", str(params.timeout)]
    if params.port is not None:
        command_arguments += ["-p", str(params.port)]
    if params.remote_version is not None:
        command_arguments += ["-r", replace_macros(params.remote_version, host_config.macros)]
    if params.remote_protocol is not None:
        command_arguments += ["-P", replace_macros(params.remote_protocol, host_config.macros)]

    description = (
        replace_macros(params.description, host_config.macros) if params.description else ""
    )
    yield ActiveCheckCommand(
        service_description=f"SSH {description}" if description else "SSH",
        command_arguments=command_arguments,
    )


active_check_ssh = ActiveCheckConfig(
    name="ssh",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
