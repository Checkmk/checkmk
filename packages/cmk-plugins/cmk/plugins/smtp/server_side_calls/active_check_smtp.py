#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    replace_macros,
    Secret,
)

_LevelsModel = tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]


class AuthParameters(BaseModel):
    username: str
    password: Secret


_IpFamilyTag = Literal["primary", "ipv4", "ipv6"]


class Parameters(BaseModel):
    name: str
    hostname: str | None = None
    expect: str | None = None
    port: int | None = None
    address_family: _IpFamilyTag = "primary"
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
    # return host and address family to use
    target_host = replace_macros(params.hostname, host_config.macros) if params.hostname else None
    if ip_config := _get_host_ip_config(host_config, params.address_family):
        host = target_host or ip_config.address
        return host, "-4" if ip_config.family is IPAddressFamily.IPV4 else "-6"

    if target_host:
        # special case to keep compatibility with 2.3 and earlier
        # WATO has configured hostname in check but family as primary, which is absent
        if params.address_family == "primary":
            return target_host, "-4"

        return target_host, "-4" if params.address_family == "ipv4" else "-6"

    if params.address_family == "ipv6":
        # special case: ipv6 is enforced and must be presented in host config
        raise ValueError("IPv6 is not configured for host")

    # standard case, hostname is absent( by active check) and IP stack is absent too
    raise ValueError("Host IP stack absent")


def _get_host_ip_config(
    host_config: HostConfig, tag: _IpFamilyTag
) -> IPv6Config | IPv4Config | None:
    # returns None if we have to deal with NoIp host
    match tag:
        case "ipv4":  # in GUI  it means ANY config
            return host_config.ipv4_config or host_config.ipv6_config
        case "ipv6":
            return host_config.ipv6_config
        case "primary":
            try:
                primary = host_config.primary_ip_config
                assert isinstance(primary, IPv6Config | IPv4Config)  # keep mypy happy
                return primary
            except ValueError:
                # to catch host_config.primary_ip_config exception
                return None


def check_smtp_arguments(
    params: Parameters, host_config: HostConfig
) -> Iterable[ActiveCheckCommand]:
    yield ActiveCheckCommand(
        service_description=_check_smtp_desc(params.name, host_config),
        command_arguments=_create_commad_line(params, host_config),
    )


def _create_commad_line(params: Parameters, host_config: HostConfig) -> Sequence[str | Secret]:
    args: list[str | Secret] = [
        *(("-e", params.expect) if params.expect else ()),
        *(("-p", str(params.port)) if params.port else ()),
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

    address, ip_option = _get_ip_option(params, host_config)
    args.extend((ip_option, "-H", address))

    return args


def _check_smtp_desc(name: str, host_config: HostConfig) -> str:
    description = replace_macros(name, host_config.macros)
    return description[1:] if description.startswith("^") else f"SMTP {description}"


active_check_smtp = ActiveCheckConfig(
    name="smtp",
    parameter_parser=Parameters.model_validate,
    commands_function=check_smtp_arguments,
)
