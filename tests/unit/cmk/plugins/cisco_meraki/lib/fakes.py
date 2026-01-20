#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.plugins.cisco_meraki.lib import schema
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages

from . import factories


class _FakeApplianceSDK:
    def getOrganizationApplianceUplinkStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawUplinkStatuses]:
        uplink_statuses = {
            "123": [
                factories.RawUplinkStatusesFactory.build(networkId="1", serial="S123-1"),
                factories.RawUplinkStatusesFactory.build(networkId="1", serial="S123-2"),
            ],
            "456": [
                factories.RawUplinkStatusesFactory.build(networkId="2", serial="S456"),
            ],
        }
        return uplink_statuses.get(organizationId, [])

    def getOrganizationApplianceVpnStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawUplinkVpnStatuses]:
        uplink_statuses = {
            "123": [
                factories.RawUplinkVpnStatusesFactory.build(
                    networkName="one",
                    deviceSerial="S123-1",
                    merakiVpnPeers=[{"networkName": "one"}],
                ),
                factories.RawUplinkVpnStatusesFactory.build(
                    networkName="one",
                    deviceSerial="S123-2",
                    thirdPartyVpnPeers=[{"name": "one"}],
                ),
            ],
            "456": [
                factories.RawUplinkVpnStatusesFactory.build(networkName="two", serial="S456"),
            ],
        }
        return uplink_statuses.get(organizationId, [])

    def getOrganizationApplianceUplinksUsageByNetwork(
        self, organizationId: str, total_pages: TotalPages, timespan: int
    ) -> Sequence[schema.RawUplinkUsage]:
        example_bandwith = {"sent": 100, "received": 200}
        uplink_usage = {
            "123": [
                factories.RawUplinkUsageFactory.build(
                    networkId="1",
                    byUplink=[{"serial": "S123-1", "interface": "wan1", **example_bandwith}],
                ),
                factories.RawUplinkUsageFactory.build(
                    networkId="1",
                    byUplink=[{"serial": "S123-1", "interface": "wan2", **example_bandwith}],
                ),
            ],
            "456": [
                factories.RawUplinkUsageFactory.build(
                    networkId="2",
                    byUplink=[{"serial": "S456", "interface": "wan3", **example_bandwith}],
                ),
            ],
        }
        return uplink_usage.get(organizationId, [])

    def getDeviceAppliancePerformance(
        self, serial: str
    ) -> Sequence[schema.RawAppliancePerformance]:
        appliance_performance = {
            "S123-1": [schema.RawAppliancePerformance(perfScore=20.0)],
            "S123-2": [schema.RawAppliancePerformance(perfScore=40.0)],
            "S456": [schema.RawAppliancePerformance(perfScore=60.0)],
        }
        return appliance_performance.get(serial, [])


class _FakeOrganisationsSDK:
    def getOrganizations(self) -> Sequence[schema.RawOrganisation]:
        return [
            factories.RawOrganizationFactory.build(id="123", api={"enabled": True}),
            factories.RawOrganizationFactory.build(id="456", api={"enabled": True}),
        ]

    def getOrganizationNetworks(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawNetwork]:
        networks = {
            "123": [factories.RawNetworkFactory.build(id="1", name="one", organizationId="123")],
            "456": [factories.RawNetworkFactory.build(id="2", name="two", organizationId="456")],
        }
        return networks.get(organizationId, [])

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
                factories.RawDeviceFactory.build(
                    serial="S124-1", name="dev1", networkId="net1", productType="appliance"
                ),
                factories.RawDeviceFactory.build(
                    serial="S123-2", name="dev2", networkId="net2", productType="appliance"
                ),
                factories.RawDeviceFactory.build(
                    serial="S123-sw", name="sw1", networkId="net3", productType="switch"
                ),
                factories.RawDeviceFactory.build(
                    serial="S123-wes", name="wes1", networkId="net4", productType="wireless"
                ),
            ],
            "456": [
                factories.RawDeviceFactory.build(
                    serial="S456", name="dev3", networkId="wan1", productType="sensor"
                ),
                factories.RawDeviceFactory.build(
                    serial="S456-sw", name="sw2", networkId="wan2", productType="switch"
                ),
                factories.RawDeviceFactory.build(
                    serial="S456-wes", name="wes2", networkId="wan3", productType="wireless"
                ),
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

    def getOrganizationApiRequestsOverviewResponseCodesByInterval(
        self, organizationId: str, total_pages: TotalPages, t0: str, t1: str
    ) -> Sequence[schema.RawApiResponseCodes]:
        response_codes = {
            "123": [
                factories.RawApiResponseCodesFactory.build(),
            ],
            "456": [
                factories.RawApiResponseCodesFactory.build(),
            ],
        }
        return response_codes.get(organizationId, [])

    def getOrganizationDevicesUplinksAddressesByDevice(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawDeviceUplinksAddress]:
        uplink_addresses = {
            "123": [
                factories.RawDevicesUplinksAddressFactory.build(serial="S123-1"),
                factories.RawDevicesUplinksAddressFactory.build(serial="S123-2"),
            ],
            "456": [
                factories.RawDevicesUplinksAddressFactory.build(serial="S456"),
            ],
        }
        return uplink_addresses.get(organizationId, [])


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


class _FakeSwitchSDK:
    def getDeviceSwitchPortsStatuses(
        self, serial: str, timespan: int
    ) -> Sequence[schema.RawSwitchPortStatus]:
        switch_port_statuses = {
            "S123-sw": [factories.RawSwitchPortStatusFactory.build()],
            "S456-sw": [factories.RawSwitchPortStatusFactory.build()],
        }
        return switch_port_statuses.get(serial, [])


class _FakeWirelessSDK:
    def getDeviceWirelessStatus(self, serial: str) -> Sequence[schema.RawWirelessDeviceStatus]:
        wireless_statuses = {
            "S123-wes": [factories.RawWirelessDeviceStatusFactory.build()],
            "S456-wes": [factories.RawWirelessDeviceStatusFactory.build()],
        }
        return wireless_statuses.get(serial, [])

    def getOrganizationWirelessDevicesEthernetStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawWirelessEthernetStatus]:
        wireless_statuses = {
            "123": [
                factories.RawWirelessEthernetStatusFactory.build(serial="S123-wes", name="wes1"),
            ],
            "456": [
                factories.RawWirelessEthernetStatusFactory.build(serial="S456-wes", name="wes2"),
            ],
        }
        return wireless_statuses.get(organizationId, [])


class FakeMerakiSDK:
    def __init__(self) -> None:
        self._appliance = _FakeApplianceSDK()
        self._organizations = _FakeOrganisationsSDK()
        self._sensor = _FakeSensorSDK()
        self._switch = _FakeSwitchSDK()
        self._wireless = _FakeWirelessSDK()

    @property
    def appliance(self) -> _FakeApplianceSDK:
        return self._appliance

    @property
    def organizations(self) -> _FakeOrganisationsSDK:
        return self._organizations

    @property
    def sensor(self) -> _FakeSensorSDK:
        return self._sensor

    @property
    def switch(self) -> _FakeSwitchSDK:
        return self._switch

    @property
    def wireless(self) -> _FakeWirelessSDK:
        return self._wireless
