#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret

from ..lib.special_agent import InfoSelection, QueryType


class Params(BaseModel):
    user: str
    secret: Secret
    direct: tuple[QueryType, list[InfoSelection]]
    tcp_port: int | None = None
    ssl: (
        tuple[Literal["deactivated"], None]
        | tuple[Literal["hostname"], None]
        | tuple[Literal["custom_hostname"], str]
    )
    timeout: int | None = None
    skip_placeholder_vms: bool
    host_pwr_display: str | None = None
    vm_pwr_display: str | None = None
    snapshots_on_host: bool
    vm_piggyname: str | None = None
    spaces: str

    @property
    def infos(self) -> list[InfoSelection]:
        return self.direct[1]


def commands_function(params: Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []
    if params.tcp_port is not None:
        command_arguments += ["-p", "%d" % params.tcp_port]

    command_arguments += ["-u", params.user]
    command_arguments += [params.secret.unsafe("-s=%s")]
    command_arguments += ["-i", ",".join(params.infos)]

    if params.direct[0] == QueryType.HOST_SYSTEM:
        command_arguments += ["--direct", "--hostname", host_config.name]

    if params.skip_placeholder_vms:
        command_arguments.append("-P")

    if params.spaces:
        command_arguments += ["--spaces", params.spaces]

    if params.timeout:
        command_arguments += ["--timeout", str(params.timeout)]

    if params.vm_pwr_display:
        command_arguments += ["--vm_pwr_display", params.vm_pwr_display]

    if params.vm_piggyname:
        command_arguments += ["--vm_piggyname", params.vm_piggyname]

    if params.host_pwr_display:
        command_arguments += ["--host_pwr_display", params.host_pwr_display]

    if params.snapshots_on_host:
        command_arguments += ["--snapshots-on-host"]

    if params.ssl[0] == "deactivated":
        command_arguments += ["--no-cert-check"]
    elif params.ssl[0] == "hostname":
        command_arguments += ["--cert-server-name", host_config.name]
    else:
        command_arguments += ["--cert-server-name", params.ssl[1]]

    try:
        command_arguments.append(host_config.primary_ip_config.address)
    except ValueError:
        command_arguments.append(host_config.name)

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_vsphere = SpecialAgentConfig(
    name="vsphere",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
