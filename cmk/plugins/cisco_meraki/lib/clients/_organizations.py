#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError

from cmk.plugins.cisco_meraki.lib import log, schema
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class OrganizationsSDK(Protocol):
    def getOrganizations(self) -> Sequence[schema.RawOrganisation]: ...
    def getOrganizationApiRequestsOverviewResponseCodesByInterval(
        self, organizationId: str, total_pages: TotalPages, t0: str, t1: str
    ) -> Sequence[schema.RawApiResponseCodes]: ...
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
            log.LOGGER.debug("Get organisations: %(error)r", {"error": e})
            return []

    def get_api_response_codes(self, id: str, /) -> Sequence[schema.RawApiResponseCodes]:  # noqa: A002
        try:
            return self._sdk.getOrganizationApiRequestsOverviewResponseCodesByInterval(
                id,
                total_pages="all",
                t0=time.strftime("%Y-%m-%dT%H:%M:%MZ", time.gmtime(time.time() - 120)),
                t1=time.strftime("%Y-%m-%dT%H:%M:%MZ", time.gmtime()),
            )
        except APIError as e:
            log.LOGGER.debug(f"Get API response codes {id}: {e}")
            return []

    def get_devices(self, id: str, /) -> Sequence[schema.RawDevice]:  # noqa: A002
        return self._sdk.getOrganizationDevices(id, total_pages="all")

    def get_device_statuses(self, id: str, /) -> Sequence[schema.RawDevicesStatus]:  # noqa: A002
        try:
            return self._sdk.getOrganizationDevicesStatuses(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %(org_id)r: Get device statuses: %(error)r",
                {"org_id": id, "error": e},
            )
            return []

    def get_device_uplink_addresses(self, id: str, /) -> Sequence[schema.RawDeviceUplinksAddress]:  # noqa: A002
        try:
            return self._sdk.getOrganizationDevicesUplinksAddressesByDevice(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %(org_id)r: Get device uplink addresses: %(error)r",
                {"org_id": id, "error": e},
            )
            return []

    def get_licenses_overview(self, id: str, name: str, /) -> schema.LicensesOverview | None:  # noqa: A002
        try:
            raw_overview = self._sdk.getOrganizationLicensesOverview(id)
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %(org_id)r: Get license overview: %(error)r",
                {"org_id": id, "error": e},
            )
            return None

        return schema.LicensesOverview(organisation_id=id, organisation_name=name, **raw_overview)

    def get_networks(self, id: str, name: str, /) -> Sequence[schema.Network]:  # noqa: A002
        try:
            return [
                schema.Network(organizationName=name, **raw_network)
                for raw_network in self._sdk.getOrganizationNetworks(id, total_pages="all")
            ]
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %(org_id)r: Get networks: %(error)r",
                {"org_id": id, "error": e},
            )
            return []
