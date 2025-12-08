#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib import log, schema
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class WirelessSDK(Protocol):
    def getOrganizationWirelessDevicesEthernetStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[schema.RawWirelessEthernetStatus]: ...


class WirelessClient:
    def __init__(self, sdk: WirelessSDK) -> None:
        self._sdk = sdk

    def get_ethernet_statuses(self, id: str, /) -> Sequence[schema.RawWirelessEthernetStatus]:
        try:
            return self._sdk.getOrganizationWirelessDevicesEthernetStatuses(id, total_pages="all")
        except APIError as e:
            log.LOGGER.debug(
                "Organisation ID: %r: Get wireless devices ethernet statuses: %r", id, e
            )
            return []
