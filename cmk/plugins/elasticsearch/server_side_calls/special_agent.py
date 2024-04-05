#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# {
#     'port': 443,
#     'password': 'baem',
#     'infos': ['cluster_health', 'nodestats', 'stats'],
#     'user': 'blub'
# }


from collections.abc import Iterable, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    noop_parser,
    parse_secret,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_elasticsearch_arguments(
    params: Mapping[str, object], hostconfig: HostConfig, proxy_config: Mapping[str, HTTPProxy]
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "-P",
        str(params["protocol"]),
        "-m",
        *(str(i) for i in params["infos"]),  # type: ignore[attr-defined]
    ]

    if "user" in params:
        args.extend(["-u", str(params["user"])])
    if "password" in params:
        args.extend(["-s", parse_secret(params["password"])])  # type: ignore[misc]
    if "port" in params:
        args.extend(["-p", str(params["port"])])
    if params.get("no-cert-check", False):
        args.append("--no-cert-check")

    args.extend(replace_macros(str(h), hostconfig.macros) for h in params["hosts"])  # type: ignore[attr-defined]

    yield SpecialAgentCommand(args)


special_agent_elasticsearch = SpecialAgentConfig(
    name="elasticsearch",
    parameter_parser=noop_parser,
    commands_function=_agent_elasticsearch_arguments,
)
