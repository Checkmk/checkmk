#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
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
    instance: str | None = None
    port: int | None = None
    user: str
    password: Secret
    protocol: Literal["http", "https"]
    sections: Sequence[str]


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    args = [
        "-P",
        params.protocol,
        "-m",
        ",".join(params.sections),
        "-u",
        params.user,
        "-s",
        params.password.unsafe(),
        "--hostname",
        (
            replace_macros(params.instance, host_config.macros)
            if params.instance is not None
            else host_config.name
        ),
    ]

    if params.port is not None:
        args += ["-p", str(params.port)]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_rabbitmq = SpecialAgentConfig(
    name="rabbitmq",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
