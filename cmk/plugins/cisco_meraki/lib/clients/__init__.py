#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, Self

from cmk.plugins.cisco_meraki.lib.cache import cache_ttl
from cmk.plugins.cisco_meraki.lib.config import MerakiConfig
from cmk.plugins.cisco_meraki.lib.constants import AGENT
from cmk.plugins.cisco_meraki.lib.schema import Organisation
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


@dataclass(frozen=True, kw_only=True)
class MerakiClient:
    get_devices: Devices
    get_devices_statuses: DevicesStatuses
    get_licenses_overview: LicensesOverview
    get_organizations: Callable[[], Sequence[Organisation]]
    get_sensor_readings: SensorReadings

    @classmethod
    def build(cls, sdk: MerakiSDK, config: MerakiConfig) -> Self:
        organizations_storage = Storage(f"{AGENT}_organizations", config.hostname)
        cache_organizations = cache_ttl(organizations_storage, ttl=86_400)

        return cls(
            get_devices=Devices(sdk.organizations),
            get_devices_statuses=DevicesStatuses(sdk.organizations),
            get_licenses_overview=LicensesOverview(sdk.organizations),
            get_organizations=cache_organizations(Organizations(sdk.organizations)),
            get_sensor_readings=SensorReadings(sdk.sensor),
        )


__all__ = ["MerakiClient"]
