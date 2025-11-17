#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Protocol, Self

from cmk.plugins.cisco_meraki.lib import schema
from cmk.plugins.cisco_meraki.lib.cache import cache_ttl
from cmk.plugins.cisco_meraki.lib.config import MerakiConfig
from cmk.plugins.cisco_meraki.lib.constants import AGENT
from cmk.server_side_programs.v1_unstable import Storage

from ._devices import Devices, DevicesSDK
from ._devices_statuses import DevicesStatuses, DevicesStatusesSDK
from ._licenses_overview import LicensesOverview, LicensesOverviewSDK
from ._organizations import Organizations, OrganizationsSDK
from ._sensor_readings import SensorReadings, SensorReadingsSDK


class OrganizationSDK(
    DevicesSDK,
    DevicesStatusesSDK,
    LicensesOverviewSDK,
    OrganizationsSDK,
    Protocol,
): ...


class SensorSDK(
    SensorReadingsSDK,
    Protocol,
): ...


class MerakiSDK(Protocol):
    @property
    def organizations(self) -> OrganizationSDK: ...
    @property
    def sensor(self) -> SensorSDK: ...


class OrganisationCallable[T](Protocol):
    def __call__(self, id_: str, name: str) -> T: ...


@dataclass(frozen=True, kw_only=True)
class MerakiClient:
    get_devices: OrganisationCallable[dict[str, schema.Device]]
    get_devices_statuses: Callable[[str], Sequence[schema.RawDevicesStatus]]
    get_licenses_overview: OrganisationCallable[schema.LicensesOverview | None]
    get_organizations: Callable[[], Sequence[schema.Organisation]]
    get_sensor_readings: Callable[[str], Sequence[schema.RawSensorReadings]]

    @classmethod
    def build(cls, sdk: MerakiSDK, config: MerakiConfig) -> Self:
        if config.no_cache:
            return cls(
                get_devices=Devices(sdk.organizations),
                get_devices_statuses=DevicesStatuses(sdk.organizations),
                get_licenses_overview=LicensesOverview(sdk.organizations),
                get_organizations=Organizations(sdk.organizations),
                get_sensor_readings=SensorReadings(sdk.sensor),
            )

        HostStorage = partial(Storage, host=config.hostname)

        devices_storage = HostStorage(f"{AGENT}_devices")
        devices_statuses_storage = HostStorage(f"{AGENT}_devices_statuses")
        licenses_overview_storage = HostStorage(f"{AGENT}_licenses_overview")
        organizations_storage = HostStorage(f"{AGENT}_organizations")
        sensor_readings_storage = HostStorage(f"{AGENT}_sensor_readings")

        # TODO: ttl values should eventually be passed down through the configuration.
        cache_devices = cache_ttl(devices_storage, ttl=60)
        cache_devices_statuses = cache_ttl(devices_statuses_storage, ttl=60)
        cache_licenses_overview = cache_ttl(licenses_overview_storage, ttl=600)
        cache_organizations = cache_ttl(organizations_storage, ttl=600)
        cache_sensor_readings = cache_ttl(sensor_readings_storage, ttl=0)

        return cls(
            get_devices=cache_devices(Devices(sdk.organizations)),
            get_devices_statuses=cache_devices_statuses(DevicesStatuses(sdk.organizations)),
            get_licenses_overview=cache_licenses_overview(LicensesOverview(sdk.organizations)),
            get_organizations=cache_organizations(Organizations(sdk.organizations)),
            get_sensor_readings=cache_sensor_readings(SensorReadings(sdk.sensor)),
        )


__all__ = ["MerakiClient"]
