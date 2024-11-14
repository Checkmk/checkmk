#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# {
#     'tcp_port': 443,
#     'secret': 'wef',
#     'infos': ['hostsystem', 'virtualmachine'],
#     'user': 'wefwef'
# }


# mypy: disable-error-code="list-item"

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class Params(BaseModel):
    user: str
    secret: Secret
    direct: str
    tcp_port: int | None = None
    ssl: bool | str
    timeout: int | None = None
    infos: Sequence[str]
    skip_placeholder_vms: bool
    ignore_templates: bool
    host_pwr_display: str | None = None
    vm_pwr_display: str | None = None
    snapshots_on_host: bool
    vm_piggyname: str | None = None
    spaces: str


def commands_function(  # pylint: disable=too-many-branches
    params: Params, host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = []
    if params.tcp_port is not None:
        command_arguments += ["-p", "%d" % params.tcp_port]

    command_arguments += ["-u", params.user]
    command_arguments += [f"-s={params.secret.unsafe()}"]
    command_arguments += ["-i", ",".join(params.infos)]

    #  host_system: Queried host is a host system
    #  vcenter: Queried host is the vCenter
    if params.direct == "host_system":
        command_arguments += ["--direct", "--hostname", host_config.name]

    if params.skip_placeholder_vms:
        command_arguments.append("-P")
    
    if params.ignore_templates:
        command_arguments.append("-T")

    if params.spaces:
        command_arguments += ["--spaces", params.spaces]

    if params.timeout:
        command_arguments += ["--timeout", params.timeout]

    if params.vm_pwr_display:
        command_arguments += ["--vm_pwr_display", params.vm_pwr_display]

    if params.vm_piggyname:
        command_arguments += ["--vm_piggyname", params.vm_piggyname]

    if params.host_pwr_display:
        command_arguments += ["--host_pwr_display", params.host_pwr_display]

    if params.snapshots_on_host:
        command_arguments += ["--snapshots-on-host"]

    cert_verify = params.ssl
    if cert_verify is False:
        command_arguments += ["--no-cert-check"]
    elif cert_verify is True:
        command_arguments += ["--cert-server-name", host_config.name]
    else:
        command_arguments += ["--cert-server-name", cert_verify]

    command_arguments.append(host_config.primary_ip_config.address)

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_vsphere = SpecialAgentConfig(
    name="vsphere",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
