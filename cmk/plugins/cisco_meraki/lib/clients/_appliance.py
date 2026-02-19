#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib import log, schema
from cmk.plugins.cisco_meraki.lib.constants import DEFAULT_TIMESPAN
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class ApplianceSDK(Protocol):
    def getDeviceAppliancePerformance(self, serial: str) -> schema.RawAppliancePerformance: ...
    def getOrganizationApplianceUplinkStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawUplinkStatuses]: ...
    def getOrganizationApplianceUplinksUsageByNetwork(
        self, organizationId: str, total_pages: TotalPages, timespan: int
    ) -> Sequence[schema.RawUplinkUsage]: ...
    def getOrganizationApplianceVpnStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawUplinkVpnStatuses]: ...


class ApplianceClient:
    def __init__(self, sdk: ApplianceSDK) -> None:
        self._sdk = sdk

    def get_appliance_performance(self, serial: str, /) -> schema.RawAppliancePerformance | None:
        try:
            return self._sdk.getDeviceAppliancePerformance(serial)
        except APIError as e:
            log.LOGGER.debug("Serial: %r: Get appliance device performance: %r", serial, e)
            return None

    def get_uplink_statuses(self, id: str) -> Sequence[schema.RawUplinkStatuses]:
        try:
            return self._sdk.getOrganizationApplianceUplinkStatuses(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %r: Get Appliance uplink status by network: %r", id, e
            )
            return []

    def get_uplink_usage(self, id: str, /) -> Sequence[schema.RawUplinkUsage]:
        try:
            return self._sdk.getOrganizationApplianceUplinksUsageByNetwork(
                organizationId=id, total_pages="all", timespan=DEFAULT_TIMESPAN
            )
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %r: Get Appliance uplink usage by network: %r", id, e
            )
            return []

    def get_uplink_vpn_statuses(self, id: str, /) -> Sequence[schema.RawUplinkVpnStatuses]:
        try:
            return self._sdk.getOrganizationApplianceVpnStatuses(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug("Organisation ID: %r: Get Appliance VPN status by network: %r", id, e)
            return []
