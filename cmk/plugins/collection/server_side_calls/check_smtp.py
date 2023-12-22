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
    parse_secret,
    Secret,
)


class Parameters(BaseModel):
    name: str
    hostname: str | None = None
    expect: str | None = None
    port: int | None = None
    address_family: str | None = None
    commands: list[str] | None = None
    command_responses: list[str] | None = None
    from_address: str | None = None
    fqdn: str | None = None
    cert_days: tuple[int, int] | None = None
    starttls: bool = False
    auth: tuple[str, tuple[Literal["password", "store"], str]] | None = None
    response_time: tuple[float, float] | None = None
    timeout: int | None = None


def _get_ip_option(params: Parameters, host_config: HostConfig) -> tuple[str, Literal["-6", "-4"]]:
    # Use the address family of the monitored host by default
    address_family = params.address_family or (
        "ipv6" if host_config.ip_family is IPAddressFamily.IPV6 else "ipv4"
    )

    if address_family == "ipv6":
        # FIXME: migrating to the new API revealed that these can be none. Should we raise?
        # I think this is what happend before (silly as it is)
        return host_config.ipv6address or "", "-6"
    return host_config.ipv4address or "", "-4"


def check_smtp_arguments(  # pylint: disable=too-many-branches
    params: Parameters, host_config: HostConfig, _proxies: object
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
        args.extend(("-f", params.from_address))

    if params.response_time:
        warn, crit = params.response_time
        args.extend(("-w", "%0.4f" % warn, "-c", "%0.4f" % crit))

    if params.timeout is not None:
        args.extend(("-t", str(params.timeout)))

    if params.auth:
        username, password = params.auth
        args.extend(("-A", "LOGIN", "-U", username, "-P", parse_secret(password)))

    if params.starttls:
        args.append("-S")

    if params.fqdn:
        args.extend(("-F", params.fqdn))

    if params.cert_days:
        warn, crit = params.cert_days
        args.extend(("-D", f"{warn},{crit}"))

    args.extend(("-H", params.hostname if params.hostname else address))

    yield ActiveCheckCommand(
        service_description=_check_smtp_desc(params.name),
        command_arguments=args,
    )


def _check_smtp_desc(name: str) -> str:
    return name[1:] if name.startswith("^") else f"SMTP {name}"


active_check_smtp = ActiveCheckConfig(
    name="smtp",
    parameter_parser=Parameters.model_validate,
    commands_function=check_smtp_arguments,
)
