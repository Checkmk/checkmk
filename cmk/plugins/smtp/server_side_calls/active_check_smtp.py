#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    replace_macros,
    Secret,
)

_LevelsModel = tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]


class AuthParameters(BaseModel):
    username: str
    password: Secret


class Parameters(BaseModel):
    name: str
    hostname: str | None = None
    expect: str | None = None
    port: int | None = None
    address_family: Literal["primary", "ipv4", "ipv6"] = "primary"
    commands: list[str] | None = None
    command_responses: list[str] | None = None
    from_address: str | None = None
    fqdn: str | None = None
    cert_days: _LevelsModel = ("no_levels", None)
    starttls: bool = False
    auth: AuthParameters | None = None
    response_time: _LevelsModel = ("no_levels", None)
    timeout: int | None = None


def _get_ip_option(params: Parameters, host_config: HostConfig) -> tuple[str, Literal["-6", "-4"]]:
    # Use the address family of the monitored host by default
    used_family = (
        params.address_family
        if params.address_family != "primary"
        else ("ipv6" if host_config.primary_ip_config.family is IPAddressFamily.IPV6 else "ipv4")
    )

    if used_family == "ipv6":
        if (ipv6 := host_config.ipv6_config) is None:
            raise ValueError("IPv6 is not configured for host")
        return ipv6.address, "-6"

    if (ipv4 := host_config.ipv4_config) is None:
        raise ValueError("IPv4 is not configured for host")
    return ipv4.address, "-4"


def check_smtp_arguments(
    params: Parameters, host_config: HostConfig
) -> Iterable[ActiveCheckCommand]:
    address, ip_option = _get_ip_option(params, host_config)

    args: list[str | Secret] = [
        *(("-e", params.expect) if params.expect else ()),
        *(("-p", str(params.port)) if params.port else ()),
        ip_option,
    ]
    for s in params.commands or ():
        args.extend(("-C", s))

    for s in params.command_responses or ():
        args.extend(("-R", s))

    if params.from_address:
        args.extend(("-f", replace_macros(params.from_address, host_config.macros)))

    if params.response_time[1]:
        warn, crit = params.response_time[1]
        args.extend(("-w", "%0.4f" % warn, "-c", "%0.4f" % crit))

    if params.timeout is not None:
        args.extend(("-t", f"{params.timeout:.0f}"))

    if params.auth:
        args.extend(
            ("-A", "LOGIN", "-U", params.auth.username, "-P", params.auth.password.unsafe())
        )

    if params.starttls:
        args.append("-S")

    if params.fqdn:
        args.extend(("-F", replace_macros(params.fqdn, host_config.macros)))

    if params.cert_days[1]:
        warn = params.cert_days[1][0] / 86400.0
        crit = params.cert_days[1][1] / 86400.0
        args.extend(("-D", f"{warn:.0f},{crit:.0f}"))

    address = replace_macros(params.hostname, host_config.macros) if params.hostname else address
    args.extend(("-H", address))

    yield ActiveCheckCommand(
        service_description=_check_smtp_desc(params.name, host_config),
        command_arguments=args,
    )


def _check_smtp_desc(name: str, host_config: HostConfig) -> str:
    description = replace_macros(name, host_config.macros)
    return description[1:] if description.startswith("^") else f"SMTP {description}"


active_check_smtp = ActiveCheckConfig(
    name="smtp",
    parameter_parser=Parameters.model_validate,
    commands_function=check_smtp_arguments,
)
