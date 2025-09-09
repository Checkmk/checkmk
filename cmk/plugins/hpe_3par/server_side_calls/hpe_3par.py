#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class HPE3ParParams(BaseModel):
    user: str
    password: Secret
    port: int
    verify_cert: bool = False
    values: Sequence[str] = []


def generate_hpe_3par_command(
    params: HPE3ParParams,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--user",
        params.user,
        "--password",
        params.password.unsafe(),
        "--port",
        str(params.port),
    ]
    if not params.verify_cert:
        args.append("--no-cert-check")

    if params.values:
        args += ["--values", ",".join(params.values)]

    args.append(host_config.primary_ip_config.address)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_hpe_3par = SpecialAgentConfig(
    name="three_par",
    parameter_parser=HPE3ParParams.model_validate,
    commands_function=generate_hpe_3par_command,
)
