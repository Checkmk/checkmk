#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Container
from dataclasses import dataclass

from cmk.utils.type_defs import ValidatedString

__all__ = ["InventoryPluginName", "HWSWInventoryParameters"]


class InventoryPluginName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()


@dataclass(frozen=True)
class HWSWInventoryParameters:
    hw_changes: int
    sw_changes: int
    sw_missing: int

    # Do not use source states which would overwrite "State when
    # inventory fails" in the ruleset "Do hardware/software Inventory".
    # These are handled by the "Check_MK" service
    fail_status: int
    status_data_inventory: bool

    @classmethod
    def from_raw(cls, raw_parameters: dict) -> HWSWInventoryParameters:
        return cls(
            hw_changes=int(raw_parameters.get("hw-changes", 0)),
            sw_changes=int(raw_parameters.get("sw-changes", 0)),
            sw_missing=int(raw_parameters.get("sw-missing", 0)),
            fail_status=int(raw_parameters.get("inv-fail-status", 1)),
            status_data_inventory=bool(raw_parameters.get("status_data_inventory", False)),
        )
