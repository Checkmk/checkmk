#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Self

from meraki import DashboardAPI  # type: ignore[import-not-found]

from cmk.server_side_programs.v1_unstable import Storage

from . import cache, constants, schema


@dataclass(frozen=True)
class MerakiConfig:
    hostname: str
    org_ids: Sequence[str]
    org_id_as_prefix: bool
    net_id_as_prefix: bool
    no_cache: bool
    timespan: int
    cache: _CacheConfig
    required: _RequiredSections

    @classmethod
    def build(cls, args: Namespace) -> Self:
        return cls(
            hostname=args.hostname,
            org_ids=args.orgs,
            org_id_as_prefix=args.org_id_as_prefix,
            net_id_as_prefix=args.net_id_as_prefix,
            no_cache=args.no_cache,
            timespan=args.timespan,
            cache=_CacheConfig.build(args),
            required=_RequiredSections.build(set(args.sections)),
        )


def get_meraki_dashboard(api_key: str, region: str, debug: bool, proxy: str | None) -> DashboardAPI:
    match region:
        case "canada":
            base_url = "https://api.meraki.ca/api/v1"
        case "china":
            base_url = "https://api.meraki.cn/api/v1"
        case "india":
            base_url = "https://api.meraki.in/api/v1"
        case "us_gov":
            base_url = "https://api.gov-meraki.com/api/"
        case _:
            base_url = "https://api.meraki.com/api/v1"

    return DashboardAPI(
        api_key=api_key,
        base_url=base_url,
        print_console=True,
        output_log=False,
        suppress_logging=not (debug),
        # TODO: dashboard api always expects a string, but proxy can be None.
        requests_proxy=proxy,
    )


type _CacheDecorator[**P, R] = Callable[[Callable[P, R]], Callable[P, R]]


@dataclass(frozen=True)
class _CacheConfig:
    appliance_uplinks: _CacheDecorator[[str], Sequence[schema.RawUplinkStatuses]]
    appliance_vpns: _CacheDecorator[[str], Sequence[schema.RawUplinkVpnStatuses]]
    devices: _CacheDecorator[[str], Sequence[schema.RawDevice]]
    device_statuses: _CacheDecorator[[str], Sequence[schema.RawDevicesStatus]]
    device_uplinks_info: _CacheDecorator[[str], Sequence[schema.RawDeviceUplinksAddress]]
    licenses_overview: _CacheDecorator[[str, str], schema.LicensesOverview | None]
    networks: _CacheDecorator[[str, str], Sequence[schema.Network]]
    organizations: _CacheDecorator[[], Sequence[schema.RawOrganisation]]
    wireless_device_statuses: _CacheDecorator[[str], Sequence[schema.RawWirelessDeviceStatus]]
    wireless_ethernet_statuses: _CacheDecorator[[str], Sequence[schema.RawWirelessEthernetStatus]]

    @classmethod
    def build(cls, args: Namespace) -> Self:
        return cls(
            appliance_uplinks=cache.cache_ttl(
                Storage("cisco_meraki_appliance_uplinks", host=args.hostname),
                ttl=args.cache_appliance_uplinks,
            ),
            appliance_vpns=cache.cache_ttl(
                Storage("cisco_meraki_appliance_vpns", host=args.hostname),
                ttl=args.cache_appliance_vpns,
            ),
            devices=cache.cache_ttl(
                Storage("cisco_meraki_devices", host=args.hostname),
                ttl=args.cache_devices,
            ),
            device_statuses=cache.cache_ttl(
                Storage("cisco_meraki_devices_statuses", host=args.hostname),
                ttl=args.cache_device_statuses,
            ),
            device_uplinks_info=cache.cache_ttl(
                Storage("cisco_meraki_device_uplinks_info", host=args.hostname),
                ttl=args.cache_device_uplinks_info,
            ),
            licenses_overview=cache.cache_ttl(
                Storage("cisco_meraki_licenses_overview", host=args.hostname),
                ttl=args.cache_licenses_overview,
            ),
            networks=cache.cache_ttl(
                Storage("cisco_meraki_networks", host=args.hostname),
                ttl=args.cache_networks,
            ),
            organizations=cache.cache_ttl(
                Storage("cisco_meraki_organizations", host=args.hostname),
                ttl=args.cache_organizations,
            ),
            wireless_device_statuses=cache.cache_ttl(
                Storage("cisco_meraki_wireless_device_statuses", host=args.hostname),
                ttl=args.cache_wireless_device_statuses,
            ),
            wireless_ethernet_statuses=cache.cache_ttl(
                Storage("cisco_meraki_wireless_ethernet_statuses", host=args.hostname),
                ttl=args.cache_wireless_ethernet_statuses,
            ),
        )


@dataclass(frozen=True)
class _RequiredSections:
    api_response_codes: bool
    appliance_performance: bool
    appliance_uplinks: bool
    appliance_vpns: bool
    device_statuses: bool
    device_uplinks_info: bool
    licenses_overview: bool
    sensor_readings: bool
    switch_port_statuses: bool
    wireless_device_statuses: bool
    wireless_ethernet_statuses: bool

    @classmethod
    def build(cls, sections: set[str]) -> Self:
        return cls(
            api_response_codes=constants.SEC_NAME_API_RESPONSE_CODES in sections,
            appliance_performance=constants.SEC_NAME_APPLIANCE_PERFORMANCE in sections,
            appliance_uplinks=constants.SEC_NAME_APPLIANCE_UPLINKS in sections,
            appliance_vpns=constants.SEC_NAME_APPLIANCE_VPNS in sections,
            device_statuses=constants.SEC_NAME_DEVICE_STATUSES in sections,
            device_uplinks_info=constants.SEC_NAME_DEVICE_UPLINKS_INFO in sections,
            licenses_overview=constants.SEC_NAME_LICENSES_OVERVIEW in sections,
            sensor_readings=constants.SEC_NAME_SENSOR_READINGS in sections,
            switch_port_statuses=constants.SEC_NAME_SWITCH_PORT_STATUSES in sections,
            wireless_device_statuses=constants.SEC_NAME_WIRELESS_DEVICE_STATUSES in sections,
            wireless_ethernet_statuses=constants.SEC_NAME_WIRELESS_ETHERNET_STATUSES in sections,
        )

    @property
    def devices(self) -> bool:
        return (
            self.device_statuses
            or self.device_uplinks_info
            or self.sensor_readings
            or self.appliance_uplinks
            or self.appliance_vpns
            or self.appliance_performance
            or self.switch_port_statuses
            or self.wireless_device_statuses
            or self.wireless_ethernet_statuses
        )
