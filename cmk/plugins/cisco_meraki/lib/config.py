#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Self

from meraki import DashboardAPI  # type: ignore[import-not-found]

from cmk.server_side_programs.v1_unstable import Storage

from . import cache, constants, schema

type CacheDecorator[**P, R] = Callable[[Callable[P, R]], Callable[P, R]]


@dataclass(frozen=True)
class CacheConfig:
    devices: CacheDecorator[[str, str], dict[str, schema.Device]]
    device_statuses: CacheDecorator[[str], Sequence[schema.RawDevicesStatus]]
    licenses_overview: CacheDecorator[[str, str], schema.LicensesOverview | None]
    organizations: CacheDecorator[[], Sequence[schema.RawOrganisation]]
    sensor_readings: CacheDecorator[[str], Sequence[schema.RawSensorReadings]]

    @classmethod
    def build(cls, args: Namespace) -> Self:
        return cls(
            devices=cache.cache_ttl(
                Storage("cisco_meraki_devices", host=args.hostname),
                ttl=args.cache_devices,
            ),
            device_statuses=cache.cache_ttl(
                Storage("cisco_meraki_devices_statuses", host=args.hostname),
                ttl=args.cache_device_statuses,
            ),
            licenses_overview=cache.cache_ttl(
                Storage("cisco_meraki_licenses_overview", host=args.hostname),
                ttl=args.cache_licenses_overview,
            ),
            organizations=cache.cache_ttl(
                Storage("cisco_meraki_organizations", host=args.hostname),
                ttl=args.cache_organizations,
            ),
            sensor_readings=cache.cache_ttl(
                Storage("cisco_meraki_sensor_readings", host=args.hostname),
                ttl=args.cache_sensor_readings,
            ),
        )


@dataclass(frozen=True)
class MerakiConfig:
    hostname: str
    org_ids: Sequence[str]
    section_names: Sequence[str]
    org_id_as_prefix: bool
    no_cache: bool
    cache: CacheConfig

    @classmethod
    def build(cls, args: Namespace) -> Self:
        return cls(
            hostname=args.hostname,
            org_ids=args.orgs,
            section_names=args.sections,
            org_id_as_prefix=args.org_id_as_prefix,
            no_cache=args.no_cache,
            cache=CacheConfig.build(args),
        )

    @property
    def device_statuses_required(self) -> bool:
        return constants.SEC_NAME_DEVICE_STATUSES in self.section_names

    @property
    def licenses_overview_required(self) -> bool:
        return constants.SEC_NAME_LICENSES_OVERVIEW in self.section_names

    @property
    def sensor_readings_required(self) -> bool:
        return constants.SEC_NAME_SENSOR_READINGS in self.section_names

    @property
    def devices_required(self) -> bool:
        return self.device_statuses_required or self.sensor_readings_required


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
