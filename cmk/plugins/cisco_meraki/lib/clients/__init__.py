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
): ...


class SensorSDK(
    SensorReadingsSDK,
): ...


class MerakiSDK(Protocol):
    organizations: OrganizationSDK
    sensor: SensorSDK


@dataclass(frozen=True, kw_only=True)
class MerakiClients:
    devices: DevicesClient
    devices_statuses: DevicesStatusesClient
    licenses: LicensesClient
    organizations: OrganizationsClient
    sensor_readings: SensorReadingsClient

    @classmethod
    def build(cls, sdk: MerakiSDK) -> Self:
        return cls(
            devices=DevicesClient(sdk.organizations),
            devices_statuses=DevicesStatusesClient(sdk.organizations),
            licenses=LicensesClient(sdk.organizations),
            organizations=OrganizationsClient(sdk.organizations),
            sensor_readings=SensorReadingsClient(sdk.sensor),
        )


__all__ = ["MerakiClients"]
