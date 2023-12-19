#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from enum import Enum
from typing import assert_never, Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class PwrDisplay(Enum):
    SYSTEM = None
    HOST = "esxhost"
    VM = "vm"


class VmPiggyname(Enum):
    ALIAS = "alias"
    HOSTNAME = "hostname"


class HostnameSpaces(Enum):
    CUT = "cut"
    UNDERSCORE = "underscore"


class Params(BaseModel, frozen=True):
    user: str
    secret: tuple[Literal["password", "store"], str]
    direct: bool
    ssl: bool | str
    tcp_port: int | None = Field(None, ge=1, le=65535)
    timeout: int | None = Field(None, ge=1)
    infos: Sequence[Literal["hostsystem", "virtualmachine", "datastore", "counters", "licenses"]]
    skip_placeholder_vms: bool
    host_pwr_display: PwrDisplay | None = None
    vm_pwr_display: PwrDisplay | None = None
    snapshots_on_host: bool
    vm_piggyname: VmPiggyname | None = None
    spaces: HostnameSpaces


def commands_function(
    params: Params,
    host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    command_arguments = [
        host_config.address or host_config.name,
        "-u",
        params.user,
        "-s",
        parse_secret(*params.secret),
        "-i",
        ",".join(params.infos),
        "--spaces",
        params.spaces.value,
    ]

    if params.tcp_port:
        command_arguments += ["-p", str(params.tcp_port)]

    #  True: Queried host is a host system
    #  False: Queried host is the vCenter
    if params.direct:
        command_arguments += ["--direct", "--hostname", host_config.name]

    if params.skip_placeholder_vms:
        command_arguments.append("-P")

    if params.timeout:
        command_arguments += ["--timeout", str(params.timeout)]

    if params.vm_pwr_display:
        command_arguments += ["--vm_pwr_display", params.vm_pwr_display.value]

    if params.vm_piggyname:
        command_arguments += ["--vm_piggyname", params.vm_piggyname.value]

    if params.host_pwr_display:
        command_arguments += ["--host_pwr_display", params.host_pwr_display.value]

    if params.snapshots_on_host:
        command_arguments.append("--snapshots-on-host")

    match params.ssl:
        case bool():
            command_arguments += (
                ["--cert-server-name", host_config.name] if params.ssl else ["--no-cert-check"]
            )
        case str():
            command_arguments += ["--cert-server-name", params.ssl]
        case _:
            assert_never(params.ssl)

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_vsphere = SpecialAgentConfig(
    name="vsphere",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
