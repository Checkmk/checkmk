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

PortSpec = tuple[Literal["explicit"], int] | tuple[Literal["macro"], str]


class SQLParams(BaseModel):
    description: str
    name: str
    dbms: str
    user: str
    password: Secret
    sql: str
    host: str | None = None
    port: PortSpec | None = None
    procedure: Mapping[str, str | bool] | None = None
    text: str | None = None
    perfdata: str | None = None
    levels: tuple[str, tuple[float, float] | None] | None = None
    levels_low: tuple[str, tuple[float, float] | None] | None = None


def generate_sql_command(
    params: SQLParams,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = [
        (
            f"--hostname={replace_macros(params.host, host_config.macros)}"
            if params.host
            else f"--hostname={host_config.primary_ip_config.address}"
        ),
        f"--dbms={params.dbms}",
        f"--name={replace_macros(params.name, host_config.macros)}",
        f"--user={replace_macros(params.user, host_config.macros)}",
        "--password-reference",
        params.password,
    ]

    match params.port:
        case "explicit", int(value):
            args.append(f"--port={value}")
        case "macro", str(value):
            # trigger the potential value error here, rather than in every call
            args.append(f"--port={int(replace_macros(value, host_config.macros))}")

    if params.procedure and "useprocs" in params.procedure:
        args.append("--procedure")
        if "input" in params.procedure:
            args.append(f"--inputvars={params.procedure['input']}")

    upper = _extract_levels(params.levels)
    lower = _extract_levels(params.levels_low)

    if params.perfdata:
        args.append(f"--metrics={params.perfdata}")

    if params.levels or params.levels_low:
        warn_low, crit_low = lower
        warn_high, crit_high = upper
        args.append(f"-w{warn_low}:{warn_high}")
        args.append(f"-c{crit_low}:{crit_high}")

    if params.text:
        args.append(f"--text={params.text}")

    sql = replace_macros(params.sql, host_config.macros)
    args.append("%s" % sql.replace("\n", r"\n").replace(";", r"\;"))

    yield ActiveCheckCommand(
        service_description=replace_macros(params.description, host_config.macros),
        command_arguments=args,
    )


def _extract_levels(
    levels: tuple[str, tuple[float, float] | None] | None,
) -> tuple[str, str] | tuple[float, float]:
    match levels:
        case ("no_levels", None):
            return "", ""
        case ("fixed", (float(warn), float(crit))):
            return warn, crit
        case _:
            return "", ""


active_check_sql = ActiveCheckConfig(
    name="sql", parameter_parser=SQLParams.model_validate, commands_function=generate_sql_command
)
