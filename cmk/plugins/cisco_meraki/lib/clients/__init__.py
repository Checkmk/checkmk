#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Protocol, Self

from ._devices import DevicesClient, DevicesSDK
from ._devices_statuses import DevicesStatusesClient, DevicesStatusesSDK
from ._licenses import LicensesClient, LicensesSDK
from ._organizations import OrganizationsClient, OrganizationsSDK
from ._sensor_readings import SensorReadingsClient, SensorReadingsSDK


class OrganizationSDK(
    DevicesSDK,
    DevicesStatusesSDK,
    LicensesSDK,
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
    get_devices: DevicesClient
    get_devices_statuses: DevicesStatusesClient
    get_licenses_overview: LicensesClient
    get_organizations: OrganizationsClient
    get_sensor_readings: SensorReadingsClient

    @classmethod
    def build(cls, sdk: MerakiSDK) -> Self:
        return cls(
            get_devices=DevicesClient(sdk.organizations),
            get_devices_statuses=DevicesStatusesClient(sdk.organizations),
            get_licenses_overview=LicensesClient(sdk.organizations),
            get_organizations=OrganizationsClient(sdk.organizations),
            get_sensor_readings=SensorReadingsClient(sdk.sensor),
        )


__all__ = ["MerakiClient"]
