#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    NoProxy,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    URLProxy,
)


class Explicit(BaseModel):
    group_name: str
    resources: list[str] | None = None


class TagBased(BaseModel):
    tag: str
    condition: tuple[Literal["exists"], None] | tuple[Literal["equals"], str]


class Config(BaseModel):
    explicit: list[Explicit] | None = None
    tag_based: list[TagBased] | None = None


class AzureParams(BaseModel):
    authority: str
    subscription: str | None = None
    tenant: str
    client: str
    secret: Secret
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    services: list[str]
    config: Config
    piggyback_vms: str | None = None
    import_tags: tuple[str, str | None] | None = None
    connection_test: bool = False  # only used by quick setup


def _tag_based_args(tag_based: list[TagBased]) -> list[str]:
    args = []
    for tag_config in tag_based:
        if tag_config.condition[0] == "exists":
            args += ["--require-tag", tag_config.tag]
        if isinstance(tag_config.condition, tuple) and tag_config.condition[0] == "equals":
            args += ["--require-tag-value", tag_config.tag, tag_config.condition[1]]
    return args


def _explicit_args(explicit: list[Explicit]) -> list[str]:
    args = ["--explicit-config"]
    for group_dict in explicit:
        args.append("group=%s" % group_dict.group_name)
        if group_dict.resources:
            args.append("resources=%s" % ",".join(group_dict.resources))
    return args


def agent_azure_arguments(
    params: AzureParams, host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--tenant",
        params.tenant,
        "--client",
        params.client,
        "--secret",
        params.secret.unsafe(),
    ]
    if params.authority:
        args += [
            "--authority",
            params.authority if params.authority != "global_" else "global",
        ]
    if params.subscription:
        args += ["--subscription", params.subscription]
    if params.piggyback_vms:
        args += ["--piggyback_vms", params.piggyback_vms]

    if params.proxy:
        match params.proxy:
            case URLProxy(url=url):
                args += ["--proxy", url]
            case EnvProxy():
                args += ["--proxy", "FROM_ENVIRONMENT"]
            case NoProxy():
                args += ["--proxy", "NO_PROXY"]

    if params.services:
        args += [
            "--services",
            *[
                p.replace("Microsoft_", "Microsoft.").replace("_slash_", "/")
                for p in params.services
            ],
        ]

    config = params.config

    if config.explicit:
        args += _explicit_args(config.explicit)
    if config.tag_based:
        args += _tag_based_args(config.tag_based)

    if params.connection_test:
        args += ["--connection-test"]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_azure = SpecialAgentConfig(
    name="azure",
    parameter_parser=AzureParams.model_validate,
    commands_function=agent_azure_arguments,
)
