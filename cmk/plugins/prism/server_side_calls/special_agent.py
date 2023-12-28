#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    noop_parser,
    parse_secret,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def generate_prism_command(
    params: Mapping[str, object], host_config: HostConfig, _http_proxy: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    if not host_config.address:
        raise ValueError("No IP address available")

    args: list[str | Secret] = [
        "--server",
        host_config.address,
        "--username",
        str(params["username"]),
        "--password",
        parse_secret(params["password"]),
    ]

    if "port" in params:
        args.extend(["--port", str(params["port"])])

    yield SpecialAgentCommand(args)


special_agent_prism = SpecialAgentConfig(
    name="prism",
    parameter_parser=noop_parser,
    commands_function=generate_prism_command,
)
