#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Sequence, Mapping
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

__param = {
    'api_key': Secret(
        id=139915660185968,
        format='%s',
        pass_safely=True
    ),
    'no_cache': True,
    'org_id_as_prefix': True,
    'net_id_as_prefix': True,
    'excluded_sections': [
        'appliance_performance',
        'switch_ports_statuses',
        'wireless_device_status',
        'org_switch_ports_statuses'
    ],
    'orgs': ['1234', '670771'],
    'cache_per_section': {
        'appliance_performance': 0,
        'appliance_uplinks_usage': 0,
        'appliance_uplinks': 60,
        'appliance_vpns': 60,
        'cellular_uplinks': 60,
        'device_status': 60,
        'device_uplinks_info': 60,
        'licenses_overview': 600,
        'networks': 600,
        'api_requests_by_organization': 0,
        'org_switch_ports_statuses': 0,
        'organisations': 600,
        'sensor_readings': 0,
        'switch_ports_statuses': 0,
        'wireless_device_status': 30,
        'wireless_ethernet_statuses': 30
    }
}


class CachePerSection(BaseModel):
    appliance_performance: int | None = None
    appliance_uplinks_usage: int | None = None
    appliance_uplinks: int | None = None
    appliance_vpns: int | None = None
    cellular_uplinks: int | None = None
    device_info: int | None = None
    device_status: int | None = None
    device_uplinks_info: int | None = None
    licenses_overview: int | None = None
    networks: int | None = None
    api_requests_by_organization: int | None = None
    org_switch_ports_statuses: int | None = None
    organisations: int | None = None
    sensor_readings: int | None = None
    switch_ports_statuses: int | None = None
    wireless_device_status: int | None = None
    wireless_ethernet_statuses: int | None = None


class Params(BaseModel):
    api_key: Secret
    cache_per_section: CachePerSection | None = None
    excluded_sections: Sequence[str] | None = None
    meraki_region: str | None = None
    net_id_as_prefix: bool | None = None
    no_cache: bool | None = None
    org_id_as_prefix: bool | None = None
    orgs: Sequence[str] | None = None
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    sections: Sequence[str] | None = None

def _agent_cisco_meraki_parser(params: Mapping[str, object]) -> Params:
    # if 'api-requests-by-organization' in params.get('excluded_sections', []):
    # print(params)
    return Params.model_validate(params)


def agent_cisco_meraki_arguments(
        params: Params,
        host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    # print(params)

    args: list[str | Secret] = [
        host_config.name,
        params.api_key.unsafe(),
    ]

    match params.proxy:
        case URLProxy(url=url):
            args += ["--proxy", url]
        case EnvProxy():
            args += ["--proxy", "FROM_ENVIRONMENT"]
        case NoProxy():
            args += ["--proxy", "NO_PROXY"]

    if params.sections is not None:
        args.append("--sections")
        args += [s.replace("_", "-") for s in params.sections]

    if params.excluded_sections:
        args.append("--excluded-sections")
        args += [s.replace("_", "-") for s in params.excluded_sections]

    if params.orgs:
        args.append("--orgs")
        args += [replace_macros(org, host_config.macros) for org in params.orgs]

    if params.meraki_region:
        args += ["--region", params.meraki_region]

    if params.cache_per_section is not None:
        args.append("--cache-per-section")
        args += [
            str(cache_value) if cache_value is not None else str(default_cache) for
            cache_value, default_cache in [
                (params.cache_per_section.appliance_performance, 0),
                (params.cache_per_section.appliance_uplinks_usage, 0),
                (params.cache_per_section.appliance_uplinks, 60),
                (params.cache_per_section.appliance_vpns, 60),
                (params.cache_per_section.cellular_uplinks, 60),
                (params.cache_per_section.device_info, 60),
                (params.cache_per_section.device_status, 60),
                (params.cache_per_section.device_uplinks_info, 60),
                (params.cache_per_section.licenses_overview, 600),
                (params.cache_per_section.networks, 600),
                (params.cache_per_section.api_requests_by_organization, 0),
                (params.cache_per_section.org_switch_ports_statuses, 0),
                (params.cache_per_section.organisations, 600),
                (params.cache_per_section.sensor_readings, 0),
                (params.cache_per_section.switch_ports_statuses, 0),
                (params.cache_per_section.wireless_device_status, 30),
                (params.cache_per_section.wireless_ethernet_statuses, 30),
            ]
        ]
    #  default=[0, 0, 60, 60, 60, 60, 60, 60, 600, 600, 0, 0, 600, 0, 0, 30, 30]
    # print(args)

    if params.org_id_as_prefix is True:
        args.append("--org-id-as-prefix")

    if params.net_id_as_prefix is True:
        args.append("--net-id-as-prefix")

    if params.no_cache is True:
        args.append("--no-cache")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_cisco_meraki = SpecialAgentConfig(
    name="cisco_meraki",
    # parameter_parser=Params.model_validate,
    parameter_parser=_agent_cisco_meraki_parser,
    commands_function=agent_cisco_meraki_arguments,
)
