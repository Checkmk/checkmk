#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_http_proxy,
    parse_secret,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

from .utils import ProxyType, SecretType


class Explicit(BaseModel):
    group_name: str
    resources: Sequence[str] = []


class Config(BaseModel):
    explicit: Sequence[Explicit] = []
    tag_based: Sequence[tuple[str, str] | tuple[str, tuple[str, str]]] = []


class AzureParams(BaseModel):
    authority: str
    subscription: str | None = None
    tenant: str
    client: str
    secret: tuple[SecretType, str]
    proxy: tuple[ProxyType, str | None] | None = None
    services: Sequence[str]
    config: Config
    piggyback_vms: str | None = None
    sequential: bool = False


def generate_azure_command(  # pylint: disable=too-many-branches
    params: AzureParams, _host_config: HostConfig, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--tenant",
        params.tenant,
        "--client",
        params.client,
        "--secret",
        parse_secret(params.secret),
    ]

    args += ["--authority", params.authority]

    if params.subscription:
        args += ["--subscription", params.subscription]

    if params.piggyback_vms:
        args += ["--piggyback_vms", params.piggyback_vms]

    if params.sequential:
        args.append("--sequential")

    if params.proxy:
        args += ["--proxy", parse_http_proxy(params.proxy, http_proxies)]

    if params.services:
        args += ["--services", *params.services]

    if params.config.explicit:
        args.append("--explicit-config")
    for group_dict in params.config.explicit:
        args.append("group=%s" % group_dict.group_name)

        if group_dict.resources:
            args.append("resources=%s" % ",".join(group_dict.resources))

    for tag, requirement in params.config.tag_based:
        if requirement == "exists":
            args += ["--require-tag", tag]
        elif isinstance(requirement, tuple) and requirement[0] == "value":
            args += ["--require-tag-value", tag, requirement[1]]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_azure = SpecialAgentConfig(
    name="azure",
    parameter_parser=AzureParams.model_validate,
    commands_function=generate_azure_command,
)
