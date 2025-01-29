#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    username: str | None = None
    password: Secret | None = None
    address: str | None = None
    port: int | None = None
    client_id: str | None = None
    protocol: str | None = None
    instance_id: str | None = None


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []

    command_arguments += ["--client-id", params.client_id] if params.client_id else []
    command_arguments += ["--password", params.password.unsafe()] if params.password else []
    command_arguments += ["--port", f"{params.port}"] if params.port else []
    command_arguments += ["--protocol", params.protocol] if params.protocol else []
    command_arguments += ["--username", params.username] if params.username else []

    command_arguments += [params.address or host_config.primary_ip_config.address]

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_mqtt = SpecialAgentConfig(
    name="mqtt",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
