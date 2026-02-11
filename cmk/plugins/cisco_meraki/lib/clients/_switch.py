#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib import log, schema


class SwitchSDK(Protocol):
    def getDeviceSwitchPortsStatuses(
        self, serial: str, timespan: int
    ) -> Sequence[schema.RawSwitchPortStatus]: ...


class SwitchClient:
    def __init__(self, sdk: SwitchSDK) -> None:
        self._sdk = sdk

    def get_switch_port_statuses(self, serial: str, /) -> Sequence[schema.RawSwitchPortStatus]:
        try:
            # The minimum timespan value for this resource is 15 min (900 sec).
            # Hence, why we are not using the DEFAULT_TIMESPAN here.
            return self._sdk.getDeviceSwitchPortsStatuses(serial, timespan=900)
        except APIError as e:
            log.LOGGER.debug("Serial: %r: Get Switch Port Statuses: %r", serial, e)
            return []
