#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class NetappOntapParams(BaseModel):
    username: str
    password: Secret
    no_cert_check: bool
    fetched_resources: Sequence[str]


def generate_netapp_ontap_command(
    params: NetappOntapParams,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret]

    args = ["--hostname", host_config.primary_ip_config.address]
    args += ["--username", params.username]
    args += ["--password", params.password.unsafe()]

    args.append("--fetched-resources")
    args.extend(params.fetched_resources)

    if params.no_cert_check:
        args += ["--no-cert-check"]
    else:
        args += ["--cert-server-name", host_config.name]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_netapp_ontap = SpecialAgentConfig(
    name="netapp_ontap",
    parameter_parser=NetappOntapParams.model_validate,
    commands_function=generate_netapp_ontap_command,
)
