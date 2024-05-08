#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
    Secret,
)

_LevelsModel = tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]


class AuthParams(BaseModel):
    bind_dn: str
    password: Secret


class LDAPParams(BaseModel):
    name: str
    base_dn: str
    hostname: str | None = None
    response_time: _LevelsModel = ("no_levels", None)
    timeout: int | None = None
    attribute: str | None = None
    authentication: AuthParams | None = None
    port: int | None = None
    version: str | None = None
    ssl: bool = False


def check_ldap_desc(params: LDAPParams, macros: Mapping[str, str]) -> str:
    name = replace_macros(params.name, macros)
    if name.startswith("^"):
        return name[1:]
    return f"LDAP {name}"


def generate_ldap_commands(
    params: LDAPParams, host_config: HostConfig
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = []

    if params.hostname is not None:
        args += ["-H", replace_macros(params.hostname, host_config.macros)]
    else:
        args += ["-H", host_config.primary_ip_config.address]

    args += ["-b", replace_macros(params.base_dn, host_config.macros)]

    if (levels := params.response_time[1]) is not None:
        warn, crit = levels
        args += ["-w", f"{warn}", "-c", f"{crit}"]

    if params.timeout is not None:
        args += ["-t", f"{params.timeout:.0f}"]

    if params.attribute is not None:
        args += ["-a", params.attribute]

    if params.authentication is not None:
        args += ["-D", params.authentication.bind_dn, "-P", params.authentication.password.unsafe()]

    if params.port is not None:
        args += ["-p", str(params.port)]

    if params.version is not None:
        args += {
            "v2": ["-2"],
            "v3": ["-3"],
            "v3tls": ["-3", "-T"],
        }[params.version]

    if params.ssl:
        args.append("--ssl")

    yield ActiveCheckCommand(
        service_description=check_ldap_desc(params, host_config.macros), command_arguments=args
    )


active_check_ldap = ActiveCheckConfig(
    name="ldap",
    parameter_parser=LDAPParams.model_validate,
    commands_function=generate_ldap_commands,
)
