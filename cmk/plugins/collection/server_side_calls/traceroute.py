#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    replace_macros,
)


class TracerouteParams(BaseModel):
    dns: bool
    address_family: str | None
    method: str | None
    routers: Sequence[tuple[str, str]]


def filter_routers(
    routers: Sequence[tuple[str, str]], state: str, macros: Mapping[str, str]
) -> Sequence[str]:
    return [replace_macros(r, macros) for r, s in routers if s == state]


def generate_traceroute_command(
    params: TracerouteParams,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args = [host_config.primary_ip_config.address]

    if params.dns:
        args.append("--use_dns")

    host_ip_family = (
        "ipv6" if host_config.primary_ip_config.family == IPAddressFamily.IPV6 else "ipv4"
    )

    args.extend(
        [
            f"--probe_method={params.method or 'udp'}",
            f"--ip_address_family={params.address_family or host_ip_family}",
            "--routers_missing_warn",
            *filter_routers(params.routers, "W", host_config.macros),
            "--routers_missing_crit",
            *filter_routers(params.routers, "C", host_config.macros),
            "--routers_found_warn",
            *filter_routers(params.routers, "w", host_config.macros),
            "--routers_found_crit",
            *filter_routers(params.routers, "c", host_config.macros),
        ]
    )

    yield ActiveCheckCommand(
        service_description="Routing",
        command_arguments=args,
    )


active_check_traceroute = ActiveCheckConfig(
    name="traceroute",
    parameter_parser=TracerouteParams.model_validate,
    commands_function=generate_traceroute_command,
)
