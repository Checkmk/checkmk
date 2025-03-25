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


from collections.abc import Iterable, Mapping, Sequence

from cmk.server_side_calls.v1 import (
    HostConfig,
    noop_parser,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_elasticsearch_arguments(
    params: Mapping[str, object],
    hostconfig: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    # We're lazy with the parsing, so we need a few asserts and str()s below to please mypy.
    assert isinstance(params["hosts"], Sequence)  # of str

    args: list[str | Secret] = ["-P", str(params["protocol"])]

    if "user" in params:
        args.extend(["-u", str(params["user"])])
    if "password" in params:
        assert isinstance(secret := params["password"], Secret)
        args.extend(["-s", secret.unsafe()])
    if "port" in params:
        args.extend(["-p", str(params["port"])])
    if params.get("no_cert_check", False):
        args.append("--no-cert-check")

    if params.get("cluster_health", False):
        args.append("--cluster-health")
    if params.get("nodes", False):
        args.append("--nodes")

    if "stats" in params:
        assert isinstance(params["stats"], Sequence)
        args.extend(["--stats", *(str(i) for i in params["stats"])])

    args.append("--")  # make sure the hosts are separated from the infos
    args.extend(replace_macros(str(h), hostconfig.macros) for h in params["hosts"])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_elasticsearch = SpecialAgentConfig(
    name="elasticsearch",
    parameter_parser=noop_parser,
    commands_function=_agent_elasticsearch_arguments,
)
