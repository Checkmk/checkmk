#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class JenkinsParams(BaseModel):
    user: str
    password: Secret
    protocol: str
    instance: str
    path: str = ""
    port: int | None = None
    sections: Sequence[str] = []


def agent_jenkins_config(
    params: JenkinsParams,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "-P",
        params.protocol,
        "-u",
        params.user,
        "-s",
        params.password.unsafe(),
    ]

    if params.path:
        args += ["--path", params.path]

    if params.sections:
        args += ["-m", " ".join(params.sections)]

    if params.port:
        args += ["-p", str(params.port)]

    args.append(replace_macros(params.instance, host_config.macros))

    yield SpecialAgentCommand(command_arguments=args)


special_agent_jenkins = SpecialAgentConfig(
    name="jenkins",
    parameter_parser=JenkinsParams.model_validate,
    commands_function=agent_jenkins_config,
)
