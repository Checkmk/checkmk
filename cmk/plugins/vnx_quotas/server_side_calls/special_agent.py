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
    nas_db: str


def command_function(
    params: Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = [
        "-u",
        params.user,
        "-p",
        params.password.unsafe(),
        "--nas-db",
        params.nas_db,
    ]

    command_arguments.append(host_config.primary_ip_config.address)

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_vnx_quotas = SpecialAgentConfig(
    name="vnx_quotas",
    parameter_parser=Params.model_validate,
    commands_function=command_function,
)
