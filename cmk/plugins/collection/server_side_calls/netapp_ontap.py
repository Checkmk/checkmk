#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_secret,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class NetappOntapParams(BaseModel):
    username: str
    password: tuple[Literal["password", "store"], str]


def generate_netapp_ontap_command(  # pylint: disable=too-many-branches
    params: NetappOntapParams, host_config: HostConfig, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret]

    args = ["--hostname", host_config.address_config.ipv4_address or host_config.name]
    args += ["--username", params.username]
    args += ["--password", parse_secret(params.password)]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_netapp_ontap = SpecialAgentConfig(
    name="netapp_ontap",
    parameter_parser=NetappOntapParams.model_validate,
    commands_function=generate_netapp_ontap_command,
)
