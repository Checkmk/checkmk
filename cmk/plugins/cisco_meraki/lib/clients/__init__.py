#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Protocol

from cmk.plugins.cisco_meraki.lib import schema
from cmk.plugins.cisco_meraki.lib.config import MerakiConfig

from ._appliance import ApplianceClient, ApplianceSDK
from ._organizations import OrganizationsClient, OrganizationsSDK
from ._sensor import SensorClient, SensorSDK
from ._switch import SwitchClient, SwitchSDK
from ._wireless import WirelessClient, WirelessSDK


class MerakiSDK(Protocol):
    @property
    def appliance(self) -> ApplianceSDK: ...
    @property
    def organizations(self) -> OrganizationsSDK: ...
    @property
    def sensor(self) -> SensorSDK: ...
    @property
    def switch(self) -> SwitchSDK: ...
    @property
    def wireless(self) -> WirelessSDK: ...


class MerakiClient:
    """
    A thin wrapper around the Meraki SDK.

    The goal of this client wrapper is to provide resource wrappers to the underlying SDK.

    Each method handles whether the resource should be fetched from cache based on the config,
    returning a strong type based on the resource's underlying schema. That way the consumers
    of this client can make use strongly typed data and caching.
    """

    def __init__(self, sdk: MerakiSDK, config: MerakiConfig) -> None:
        self._no_cache = config.no_cache
        self._cache = config.cache

        self._appliance_client = ApplianceClient(sdk.appliance)
        self._org_client = OrganizationsClient(sdk.organizations)
        self._sensor_client = SensorClient(sdk.sensor)
        self._switch_client = SwitchClient(sdk.switch)
        self._wireless_client = WirelessClient(sdk.wireless)

    def get_api_response_codes(self, id: str) -> Sequence[schema.RawApiResponseCodes]:
        return self._org_client.get_api_response_codes(id)

    def get_appliance_performance(self, serial: str) -> Sequence[schema.RawAppliancePerformance]:
        return self._appliance_client.get_appliance_performance(serial)

    def get_devices(self, id: str) -> Sequence[schema.RawDevice]:
        fn = self._org_client.get_devices
        fetch = fn if self._no_cache else self._cache.devices(fn)
        return fetch(id)

    def get_devices_statuses(self, id: str) -> Sequence[schema.RawDevicesStatus]:
        fn = self._org_client.get_device_statuses
        fetch = fn if self._no_cache else self._cache.device_statuses(fn)
        return fetch(id)

    def get_device_uplink_addresses(self, id: str) -> Sequence[schema.RawDeviceUplinksAddress]:
        fn = self._org_client.get_device_uplink_addresses
        fetch = fn if self._no_cache else self._cache.device_uplinks_info(fn)
        return fetch(id)

    def get_licenses_overview(self, id: str, name: str) -> schema.LicensesOverview | None:
        fn = self._org_client.get_licenses_overview
        fetch = fn if self._no_cache else self._cache.licenses_overview(fn)
        return fetch(id, name)

    def get_networks(self, id: str, name: str) -> Sequence[schema.Network]:
        fn = self._org_client.get_networks
        fetch = fn if self._no_cache else self._cache.networks(fn)
        return fetch(id, name)

    def get_organizations(self) -> Sequence[schema.RawOrganisation]:
        return self._org_client.get_organizations()

    def get_sensor_readings(self, id: str) -> Sequence[schema.RawSensorReadings]:
        return self._sensor_client.get_sensor_readings(id)

    def get_switch_port_statuses(self, serial: str) -> Sequence[schema.RawSwitchPortStatus]:
        return self._switch_client.get_switch_port_statuses(serial)

    def get_uplink_statuses(self, id: str) -> Sequence[schema.RawUplinkStatuses]:
        fn = self._appliance_client.get_uplink_statuses
        fetch = fn if self._no_cache else self._cache.appliance_uplinks(fn)
        return fetch(id)

    def get_uplink_vpn_statuses(self, id: str) -> Sequence[schema.RawUplinkVpnStatuses]:
        fn = self._appliance_client.get_uplink_vpn_statuses
        fetch = fn if self._no_cache else self._cache.appliance_vpns(fn)
        return fetch(id)

    def get_uplink_usage(self, id: str) -> Sequence[schema.RawUplinkUsage]:
        return self._appliance_client.get_uplink_usage(id)

    def get_wireless_device_statuses(self, serial: str) -> Sequence[schema.RawWirelessDeviceStatus]:
        fn = self._wireless_client.get_device_statuses
        fetch = fn if self._no_cache else self._cache.wireless_device_statuses(fn)
        return fetch(serial)

    def get_wireless_ethernet_statuses(self, id: str) -> Sequence[schema.RawWirelessEthernetStatus]:
        fn = self._wireless_client.get_ethernet_statuses
        fetch = fn if self._no_cache else self._cache.wireless_ethernet_statuses(fn)
        return fetch(id)


__all__ = ["MerakiClient"]
