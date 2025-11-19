#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.plugins.cisco_meraki.lib import schema
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages

from . import factories


class _FakeOrganisationsSDK:
    def getOrganizations(self) -> Sequence[schema.RawOrganisation]:
        return [
            factories.RawOrganizationFactory.build(id="123", api={"enabled": True}),
            factories.RawOrganizationFactory.build(id="456", api={"enabled": True}),
        ]

    def getOrganizationLicensesOverview(self, organizationId: str) -> schema.RawLicensesOverview:
        licenses_overviews = {
            "123": factories.RawLicensesOverviewFactory.build(id="123"),
            "456": factories.RawLicensesOverviewFactory.build(id="456"),
        }
        return licenses_overviews[organizationId]

    def getOrganizationDevices(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawDevice]:
        devices = {
            "123": [
                factories.RawDeviceFactory.build(serial="S123-1", name="dev1"),
                factories.RawDeviceFactory.build(serial="S123-2", name="dev2"),
            ],
            "456": [
                factories.RawDeviceFactory.build(serial="S456", name="dev3"),
            ],
        }
        return devices.get(organizationId, [])

    def getOrganizationDevicesStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawDevicesStatus]:
        devices_statuses = {
            "123": [
                factories.RawDevicesStatusFactory.build(serial="S123-1", name="dev1"),
                factories.RawDevicesStatusFactory.build(serial="S123-2", name="dev2"),
            ],
            "456": [
                factories.RawDevicesStatusFactory.build(serial="S456", name="dev3"),
            ],
        }
        return devices_statuses.get(organizationId, [])


class _FakeSensorSDK:
    def getOrganizationSensorReadingsLatest(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawSensorReadings]:
        sensor_readings = {
            "123": [
                factories.RawSensorReadingsFactory.build(serial="S123-1"),
                factories.RawSensorReadingsFactory.build(serial="S123-2"),
            ],
            "456": [
                factories.RawSensorReadingsFactory.build(serial="S456"),
            ],
        }
        return sensor_readings.get(organizationId, [])


class FakeMerakiSDK:
    def __init__(self) -> None:
        self._organizations = _FakeOrganisationsSDK()
        self._sensor = _FakeSensorSDK()

    @property
    def organizations(self) -> _FakeOrganisationsSDK:
        return self._organizations

    @property
    def sensor(self) -> _FakeSensorSDK:
        return self._sensor
