#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"


from collections.abc import Iterator, Sequence

from pydantic import BaseModel

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


class CachePerResource(BaseModel):
    appliances: int | None = None
    devices: int | None = None
    licenses: int | None = None
    networks: int | None = None
    wireless: int | None = None


class Params(BaseModel):
    api_key: Secret
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    region: str | None = None
    sections: Sequence[str] | None = None
    orgs: Sequence[str] | None = None
    org_id_as_prefix: bool | None = None
    net_id_as_prefix: bool | None = None
    no_cache: bool | None = None
    cache_per_resource: CachePerResource | None = None


def agent_cisco_meraki_arguments(
    params: Params,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        host_config.name,
        "--apikey-id",
        params.api_key,
    ]

    match params.proxy:
        case URLProxy(url=url):
            args += ["--proxy", url]
        case EnvProxy():
            args += ["--proxy", "FROM_ENVIRONMENT"]
        case NoProxy():
            args += ["--proxy", "NO_PROXY"]

    if params.region:
        args += ["--region", params.region]

    if params.sections is not None:
        args.append("--sections")
        args += [s.replace("_", "-") for s in params.sections]

    if params.orgs is not None:
        args.append("--orgs")
        args += [replace_macros(org, host_config.macros) for org in params.orgs]

    if params.org_id_as_prefix:
        args.append("--org-id-as-prefix")

    if params.net_id_as_prefix:
        args.append("--net-id-as-prefix")

    if params.no_cache:
        args.append("--no-cache")

    if not params.no_cache and (cache_per_resource := params.cache_per_resource):
        if cache_per_resource.appliances:
            args += ["--cache-appliances", str(cache_per_resource.appliances)]
        if cache_per_resource.devices:
            args += ["--cache-devices", str(cache_per_resource.devices)]
        if cache_per_resource.licenses:
            args += ["--cache-licenses", str(cache_per_resource.licenses)]
        if cache_per_resource.networks:
            args += ["--cache-networks", str(cache_per_resource.networks)]
        if cache_per_resource.wireless:
            args += ["--cache-wireless", str(cache_per_resource.wireless)]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_cisco_meraki = SpecialAgentConfig(
    name="cisco_meraki",
    parameter_parser=Params.model_validate,
    commands_function=agent_cisco_meraki_arguments,
)
