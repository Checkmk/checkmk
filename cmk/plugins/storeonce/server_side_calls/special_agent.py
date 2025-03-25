#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    user: str
    password: Secret
    ignore_tls: bool


def commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = [
        f"--address={host_config.name}",
        f"--user={params.user}",
        f"--password={params.password.unsafe()}",
    ]

    if params.ignore_tls:
        command_arguments.append("--no-cert-check")

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_storeonce = SpecialAgentConfig(
    name="storeonce",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
