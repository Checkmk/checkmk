#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator

import pydantic

from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    NoProxy,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    URLProxy,
)


class Timeout(pydantic.BaseModel, frozen=True):
    connect: int | None = None
    read: int | None = None


class Params(pydantic.BaseModel, frozen=True):
    url: str
    shared_secret: Secret
    verify_cert: bool
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    timeout: Timeout | None = None


def commands_function(params: Params, host_config: HostConfig) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = ["--secret-id", params.shared_secret]

    if params.proxy is not None:
        match params.proxy:
            case URLProxy(url=url):
                args += ["--proxy", url]
            case EnvProxy():
                args += ["--proxy", "FROM_ENVIRONMENT"]
            case NoProxy():
                args += ["--proxy", "NO_PROXY"]

    if (timeout := params.timeout) is not None:
        if (connect := timeout.connect) is not None:
            args += ["--connect-timeout", str(connect)]
        if (read := timeout.read) is not None:
            args += ["--read-timeout", str(read)]

    if not params.verify_cert:
        args.append("--no-cert-check")

    args.append(replace_macros(params.url, host_config.macros))

    yield SpecialAgentCommand(command_arguments=args)


special_agent_rustik = SpecialAgentConfig(
    name="rustik",
    parameter_parser=Params.model_validate,
    commands_function=commands_function,
)
