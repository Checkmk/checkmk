#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)

_LevelsModel = tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]


class Parameters(BaseModel):
    port: int
    svc_description: str | None = None
    hostname: str | None = None
    response_time: _LevelsModel = ("no_levels", None)
    timeout: float | None = None
    refuse_state: Literal["ok", "warn", "crit"] | None = None
    send_string: str | None = None
    escape_send_string: Literal[True] | None = None
    expect: Sequence[str] = ()
    expect_all: Literal[True] | None = None
    jail: Literal[True] | None = None
    mismatch_state: Literal["ok", "warn", "crit"] | None = None
    delay: int | None = None
    maxbytes: int | None = None
    ssl: Literal[True] | None = None
    cert_days: _LevelsModel = ("no_levels", None)
    quit_string: str | None = None


def _add_optional_option(name: str, value: int | str | None) -> tuple[str, str] | tuple[()]:
    return () if value is None else (f"{name}", str(value))


def _add_optional_flag(name: str, value: bool | None) -> tuple[str] | tuple[()]:
    return () if value is None else (f"{name}",)


def _to_days(seconds: float) -> int:
    return int(seconds / 86400)


def _add_cert_days(cert_days: tuple[float, float] | None) -> tuple[str, str] | tuple[()]:
    return () if cert_days is None else ("-D", f"{_to_days(cert_days[0])},{_to_days(cert_days[1])}")


def _make_arguments(params: Parameters, host_address: str) -> list[str]:
    levels = params.response_time[1]
    return [
        "-p",
        str(params.port),
        *(
            (
                "-w",
                "%f" % levels[0],
                "-c",
                "%f" % levels[1],
            )
            if levels
            else ()
        ),
        *(_add_optional_option("-t", int(params.timeout) if params.timeout else None)),
        *(_add_optional_option("-r", params.refuse_state)),
        *(_add_optional_flag("--escape", params.escape_send_string)),
        *(_add_optional_option("-s", params.send_string)),
        *(o for s in params.expect for o in _add_optional_option("-e", s)),
        *(_add_optional_flag("-A", params.expect_all)),
        *(_add_optional_flag("--jail", params.jail)),
        *(_add_optional_option("-M", params.mismatch_state)),
        *(_add_optional_option("-d", params.delay)),
        *(_add_optional_option("-m", params.maxbytes)),
        *(_add_optional_flag("--ssl", params.ssl)),
        *(_add_cert_days(params.cert_days[1])),
        *(_add_optional_option("-q", params.quit_string)),
        "-H",
        host_address,
    ]


def _make_service_description(params: Parameters, macros: Mapping[str, str]) -> str:
    if params.svc_description:
        return replace_macros(params.svc_description, macros)
    return f"TCP Port {params.port}"


def make_check_tcp_commands(
    params: Parameters, host_config: HostConfig
) -> Iterable[ActiveCheckCommand]:
    if params.hostname is None:
        host_arg = host_config.primary_ip_config.address
    else:
        host_arg = replace_macros(params.hostname, host_config.macros)

    yield ActiveCheckCommand(
        service_description=_make_service_description(params, host_config.macros),
        command_arguments=_make_arguments(params, host_arg),
    )


active_check_tcp = ActiveCheckConfig(
    name="tcp",
    parameter_parser=Parameters.model_validate,
    commands_function=make_check_tcp_commands,
)
