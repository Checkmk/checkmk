#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    hostname: str | None = None
    ip_address: str | None = None
    authentication: Mapping[str, str | Secret] | None = None
    patterns: Sequence[str]
    recursive: bool | None = None


def command_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    default_ipaddress = (
        params.ip_address if params.ip_address else host_config.primary_ip_config.address
    )
    command_arguments: list[str | Secret] = [
        params.hostname if params.hostname else host_config.name,
        params.ip_address if params.ip_address else default_ipaddress,
    ]

    if params.authentication:
        command_arguments.append("--username")
        command_arguments.append(params.authentication["username"])
        command_arguments.append("--password")
        assert isinstance(password := params.authentication["password"], Secret)
        command_arguments.append(password.unsafe())

    if params.patterns:
        command_arguments.append("--patterns")
        command_arguments.extend(params.patterns)

    if params.recursive:
        command_arguments.append("--recursive")

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_smb_share = SpecialAgentConfig(
    name="smb_share",
    parameter_parser=Params.model_validate,
    commands_function=command_function,
)
