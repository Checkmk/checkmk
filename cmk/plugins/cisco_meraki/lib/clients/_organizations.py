#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib import log, schema
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class OrganizationsSDK(Protocol):
    def getOrganizations(self) -> Sequence[schema.RawOrganisation]: ...
    def getOrganizationDevices(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawDevice]: ...
    def getOrganizationDevicesStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawDevicesStatus]: ...
    def getOrganizationDevicesUplinksAddressesByDevice(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawDeviceUplinksAddress]: ...
    def getOrganizationLicensesOverview(
        self, organizationId: str
    ) -> schema.RawLicensesOverview: ...
    def getOrganizationNetworks(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawNetwork]: ...


class OrganizationsClient:
    def __init__(self, sdk: OrganizationsSDK) -> None:
        self._sdk = sdk

    def get_organizations(self) -> Sequence[schema.RawOrganisation]:
        try:
            return self._sdk.getOrganizations()
        except APIError as e:
            log.LOGGER.debug("Get organisations: %r", e)
            return []

    def get_devices(self, id: str, name: str, /) -> dict[str, schema.Device]:
        return {
            raw_device["serial"]: schema.Device(
                organisation_id=id,
                organisation_name=name,
                **raw_device,
            )
            for raw_device in self._sdk.getOrganizationDevices(id, total_pages="all")
        }

    def get_device_statuses(self, id: str, /) -> Sequence[schema.RawDevicesStatus]:
        try:
            return self._sdk.getOrganizationDevicesStatuses(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug("Organisation ID: %r: Get device statuses: %r", id, e)
            return []

    def get_device_uplink_addresses(self, id: str, /) -> Sequence[schema.RawDeviceUplinksAddress]:
        try:
            return self._sdk.getOrganizationDevicesUplinksAddressesByDevice(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug("Organisation ID: %r: Get device uplink addresses: %r", id, e)
            return []

    def get_licenses_overview(self, id: str, name: str, /) -> schema.LicensesOverview | None:
        try:
            raw_overview = self._sdk.getOrganizationLicensesOverview(id)
        except APIError as e:
            log.LOGGER.debug("Organisation ID: %r: Get license overview: %r", id, e)
            return None

        return schema.LicensesOverview(organisation_id=id, organisation_name=name, **raw_overview)

    def get_networks(self, id: str, name: str, /) -> Sequence[schema.Network]:
        try:
            return [
                schema.Network(organizationName=name, **raw_network)
                for raw_network in self._sdk.getOrganizationNetworks(id, total_pages="all")
            ]
        except APIError as e:
            log.LOGGER.debug("Organisation ID: %r: Get networks: %r", id, e)
            return []
