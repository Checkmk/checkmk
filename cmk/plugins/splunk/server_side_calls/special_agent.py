#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    instance: str | None = None
    user: str
    password: Secret
    protocol: str
    port: int | None = None
    infos: Sequence[str]


def command_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []
    hostname = host_config.name

    command_arguments += ["-P", params.protocol]
    command_arguments += ["-m", " ".join(params.infos)]
    command_arguments += ["-u", params.user]
    command_arguments += ["-s", params.password.unsafe()]

    if params.port is not None:
        command_arguments += ["-p", str(params.port)]

    if params.instance is not None:
        hostname = params.instance

    command_arguments += [hostname]

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_splunk = SpecialAgentConfig(
    name="splunk",
    parameter_parser=Params.model_validate,
    commands_function=command_function,
)
