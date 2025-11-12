#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Protocol, Self

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
    get_organizations: Organizations
    get_sensor_readings: SensorReadings

    @classmethod
    def build(cls, sdk: MerakiSDK) -> Self:
        return cls(
            get_devices=Devices(sdk.organizations),
            get_devices_statuses=DevicesStatuses(sdk.organizations),
            get_licenses_overview=LicensesOverview(sdk.organizations),
            get_organizations=Organizations(sdk.organizations),
            get_sensor_readings=SensorReadings(sdk.sensor),
        )


__all__ = ["MerakiClient"]
