#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib.log import LOGGER
from cmk.plugins.cisco_meraki.lib.schema import RawSensorReadings
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class SensorReadingsSDK(Protocol):
    def getOrganizationSensorReadingsLatest(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[RawSensorReadings]: ...


class SensorReadings:
    def __init__(self, sdk: SensorReadingsSDK) -> None:
        self._sdk = sdk

    def __call__(self, org_id: str, /) -> Sequence[RawSensorReadings]:
        try:
            return self._sdk.getOrganizationSensorReadingsLatest(org_id, total_pages="all")
        except APIError as e:
            LOGGER.debug("Organisation ID: %r: Get sensor readings: %r", org_id, e)
            return []
