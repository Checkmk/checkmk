#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)


class MKEventsParams(BaseModel):
    hostspec: str | list[str]
    show_last_log: str
    remote: str | tuple[str, int] | None = None
    ignore_acknowledged: bool = False
    application: str | None = None
    item: str | None = None


def get_mkevents_description(params: MKEventsParams, macros: Mapping[str, str]) -> str:
    item = replace_macros(params.item, macros) if params.item else params.application
    if item:
        return f"Events {item}"
    return "Events"


def generate_mkevents_command(
    params: MKEventsParams,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args = []
    if params.remote is not None:
        if isinstance(params.remote, tuple):
            ipaddress, port = params.remote
            args += ["-H", f"{replace_macros(ipaddress, host_config.macros)}:{port}"]
        elif params.remote:
            args += ["-s", replace_macros(params.remote, host_config.macros)]

    if params.ignore_acknowledged:
        args.append("-a")

    match params.show_last_log:
        case "summary":
            args.append("-l")
        case "details":
            args.append("-L")

    if isinstance(params.hostspec, list):
        hostspecs = "/".join(params.hostspec)
        args.append(replace_macros(hostspecs, host_config.macros))
    else:
        args.append(replace_macros(params.hostspec, host_config.macros))

    if params.application is not None:
        args.append(params.application)

    yield ActiveCheckCommand(
        service_description=get_mkevents_description(params, host_config.macros),
        command_arguments=args,
    )


active_check_mkevents = ActiveCheckConfig(
    name="mkevents",
    parameter_parser=MKEventsParams.model_validate,
    commands_function=generate_mkevents_command,
)
