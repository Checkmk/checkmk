#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib.log import LOGGER
from cmk.plugins.cisco_meraki.lib.schema import RawDevicesStatus
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class DevicesStatusesSDK(Protocol):
    def getOrganizationDevicesStatuses(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[RawDevicesStatus]: ...


class DevicesStatuses:
    def __init__(self, sdk: DevicesStatusesSDK) -> None:
        self._sdk = sdk

    def __call__(self, org_id: str, /) -> Sequence[RawDevicesStatus]:
        try:
            return self._sdk.getOrganizationDevicesStatuses(org_id, total_pages="all")
        except APIError as e:
            LOGGER.debug("Organisation ID: %r: Get device statuses: %r", org_id, e)
            return []
