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


class CachePerSection(BaseModel):
    appliance_uplinks: int | None = None
    appliance_vpns: int | None = None
    devices: int | None = None
    device_statuses: int | None = None
    device_uplinks_info: int | None = None
    licenses_overview: int | None = None
    networks: int | None = None
    organizations: int | None = None
    wireless_ethernet_statuses: int | None = None


class Params(BaseModel):
    api_key: Secret
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    region: str | None = None
    sections: Sequence[str] | None = None
    orgs: Sequence[str] | None = None
    org_id_as_prefix: bool | None = None
    net_id_as_prefix: bool | None = None
    no_cache: bool | None = None
    timespan: int | None = None
    cache_per_section: CachePerSection | None = None


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

    if params.timespan:
        args.append("--timespan")

    if not params.no_cache and (cache_per_section := params.cache_per_section):
        if cache_per_section.appliance_uplinks:
            args += ["--cache-appliance-uplinks", str(cache_per_section.appliance_uplinks)]
        if cache_per_section.appliance_vpns:
            args += ["--cache-appliance-vpns", str(cache_per_section.appliance_vpns)]
        if cache_per_section.devices:
            args += ["--cache-devices", str(cache_per_section.devices)]
        if cache_per_section.device_statuses:
            args += ["--cache-device-statuses", str(cache_per_section.device_statuses)]
        if cache_per_section.device_uplinks_info:
            args += ["--cache-device-uplinks-info", str(cache_per_section.device_uplinks_info)]
        if cache_per_section.licenses_overview:
            args += ["--cache-licenses-overview", str(cache_per_section.licenses_overview)]
        if cache_per_section.networks:
            args += ["--cache-networks", str(cache_per_section.networks)]
        if cache_per_section.organizations:
            args += ["--cache-organizations", str(cache_per_section.organizations)]
        if cache_per_section.wireless_ethernet_statuses:
            args += [
                "--cache-wireless-ethernet-statuses",
                str(cache_per_section.wireless_ethernet_statuses),
            ]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_cisco_meraki = SpecialAgentConfig(
    name="cisco_meraki",
    parameter_parser=Params.model_validate,
    commands_function=agent_cisco_meraki_arguments,
)
