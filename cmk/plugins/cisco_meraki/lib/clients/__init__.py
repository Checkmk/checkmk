#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Protocol

from cmk.plugins.cisco_meraki.lib import schema
from cmk.plugins.cisco_meraki.lib.config import MerakiConfig

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


class MerakiClient:
    def __init__(self, sdk: MerakiSDK, config: MerakiConfig) -> None:
        self._sdk = sdk
        self._config = config

    def get_devices(self, id: str, name: str) -> dict[str, schema.Device]:
        get_resource = Devices(self._sdk.organizations)
        if self._config.no_cache:
            return get_resource(id, name)
        return self._config.cache.devices(get_resource)(id, name)

    def get_devices_statuses(self, id: str) -> Sequence[schema.RawDevicesStatus]:
        get_resource = DevicesStatuses(self._sdk.organizations)
        if self._config.no_cache:
            return get_resource(id)
        return self._config.cache.device_statuses(get_resource)(id)

    def get_licenses_overview(self, id: str, name: str) -> schema.LicensesOverview | None:
        get_resource = LicensesOverview(self._sdk.organizations)
        if self._config.no_cache:
            return get_resource(id, name)
        return self._config.cache.licenses_overview(get_resource)(id, name)

    def get_organizations(self) -> Sequence[schema.RawOrganisation]:
        get_resource = Organizations(self._sdk.organizations)
        if self._config.no_cache:
            return get_resource()
        return self._config.cache.organizations(get_resource)()

    def get_sensor_readings(self, id: str) -> Sequence[schema.RawSensorReadings]:
        get_resource = SensorReadings(self._sdk.sensor)
        if self._config.no_cache:
            return get_resource(id)
        return self._config.cache.sensor_readings(get_resource)(id)


__all__ = ["MerakiClient"]
