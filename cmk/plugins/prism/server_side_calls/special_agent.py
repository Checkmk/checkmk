#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def generate_prism_command(
    params: Mapping[str, object],
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    assert isinstance(secret := params["password"], Secret)

    args: list[str | Secret] = [
        "--server",
        host_config.primary_ip_config.address,
        "--username",
        str(params["username"]),
        "--password",
        secret.unsafe(),
    ]

    if "port" in params:
        args.extend(["--port", str(params["port"])])

    if params["no_cert_check"]:
        args.append("--no-cert-check")
    else:
        args.extend(["--cert-server-name", host_config.name])

    if "timeout" in params:
        args.extend(["--timeout", f"{params['timeout']:.0f}"])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_prism = SpecialAgentConfig(
    name="prism",
    parameter_parser=noop_parser,
    commands_function=generate_prism_command,
)
