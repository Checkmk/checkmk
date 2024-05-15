#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig


class FTPParams(BaseModel):
    port: int | None = None
    response_time: tuple[float, float] | None = None
    timeout: int | None = None
    refuse_state: Literal["crit", "warn", "ok"] | None = None
    send_string: str | None = None
    expect: Sequence[str] = []
    ssl: bool = False
    cert_days: tuple[int, int] | None = None


def generate_ftp_command(
    params: FTPParams, host_config: HostConfig
) -> Iterator[ActiveCheckCommand]:
    args = ["-H", host_config.primary_ip_config.address]

    if params.port:
        args += ["-p", str(params.port)]

    if params.response_time:
        warn, crit = params.response_time
        args += ["-w", "%f" % (warn / 1000.0)]
        args += ["-c", "%f" % (crit / 1000.0)]

    if params.timeout:
        args += ["-t", str(params.timeout)]

    if params.refuse_state:
        args += ["-r", params.refuse_state]

    if params.send_string:
        args += ["-s", params.send_string]

    if params.expect:
        for s in params.expect:
            args += ["-e", s]

    if params.ssl:
        args.append("--ssl")

    if params.cert_days:
        warn, crit = params.cert_days
        args += ["-D", str(warn), str(crit)]

    yield ActiveCheckCommand(service_description=check_ftp_get_item(params), command_arguments=args)


def check_ftp_get_item(params: FTPParams) -> str:
    if params.port is not None and params.port != 21:
        return "FTP Port " + str(params.port)
    return "FTP"


active_check_ftp = ActiveCheckConfig(
    name="ftp", parameter_parser=FTPParams.model_validate, commands_function=generate_ftp_command
)
