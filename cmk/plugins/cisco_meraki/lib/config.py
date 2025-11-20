#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from meraki import DashboardAPI  # type: ignore[import-not-found]

from . import constants


@dataclass(frozen=True)
class CacheTTL:
    devices: float
    device_statuses: float
    licenses_overview: float
    organizations: float
    sensor_readings: float


@dataclass(frozen=True)
class MerakiConfig:
    hostname: str
    org_ids: Sequence[str]
    section_names: Sequence[str]
    org_id_as_prefix: bool
    no_cache: bool
    cache_ttl: CacheTTL

    @classmethod
    def build(cls, args: Namespace) -> Self:
        return cls(
            hostname=args.hostname,
            org_ids=args.orgs,
            section_names=args.sections,
            org_id_as_prefix=args.org_id_as_prefix,
            no_cache=args.no_cache,
            cache_ttl=CacheTTL(
                devices=args.cache_devices,
                device_statuses=args.cache_device_statuses,
                licenses_overview=args.cache_licenses_overview,
                organizations=args.cache_organizations,
                sensor_readings=args.cache_sensor_readings,
            ),
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
