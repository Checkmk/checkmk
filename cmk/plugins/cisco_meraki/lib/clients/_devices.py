#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from cmk.plugins.cisco_meraki.lib.schema import Device, RawDevice
from cmk.plugins.cisco_meraki.lib.type_defs import TotalPages


class DevicesSDK(Protocol):
    def getOrganizationDevices(
        self, organizationId: str, total_pages: TotalPages
    ) -> Sequence[RawDevice]: ...


class Devices:
    def __init__(self, sdk: DevicesSDK) -> None:
        self._sdk = sdk

    def __call__(self, id_: str, name: str) -> dict[str, Device]:
        return {
            raw_device["serial"]: Device(
                organisation_id=id_,
                organisation_name=name,
                **raw_device,
            )
            for raw_device in self._get_raw_devices(id_)
        }

    def _get_raw_devices(self, org_id: str) -> Sequence[RawDevice]:
        return self._sdk.getOrganizationDevices(org_id, total_pages="all")
