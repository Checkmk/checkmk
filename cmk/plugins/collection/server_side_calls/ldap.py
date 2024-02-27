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
    HTTPProxy,
    parse_secret,
    Secret,
)


class LDAPParams(BaseModel):
    name: str
    base_dn: str
    hostname: str | None = None
    response_time: tuple[int, int] | None = None
    timeout: int | None = None
    attribute: str | None = None
    authentication: tuple[str, tuple[Literal["password", "store"], str]] | None = None
    port: int | None = None
    version: str | None = None
    ssl: bool = False


def check_ldap_desc(params: LDAPParams) -> str:
    if (name := params.name).startswith("^"):
        return name[1:]
    return f"LDAP {name}"


def generate_ldap_commands(
    params: LDAPParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = []

    if params.hostname is not None:
        args += ["-H", params.hostname]
    else:
        if host_config.resolved_address is None:
            raise ValueError("No hostname or IP address provided")
        args += ["-H", host_config.resolved_address]

    args += ["-b", params.base_dn]

    if params.response_time is not None:
        warn, crit = params.response_time
        args += ["-w", str(warn / 1000.0), "-c", str(crit / 1000.0)]

    if params.timeout is not None:
        args += ["-t", str(params.timeout)]

    if params.attribute is not None:
        args += ["-a", params.attribute]

    if params.authentication is not None:
        binddn, password = params.authentication
        args += ["-D", binddn, "-P", parse_secret(password)]

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

    yield ActiveCheckCommand(service_description=check_ldap_desc(params), command_arguments=args)


active_check_ldap = ActiveCheckConfig(
    name="ldap",
    parameter_parser=LDAPParams.model_validate,
    commands_function=generate_ldap_commands,
)
