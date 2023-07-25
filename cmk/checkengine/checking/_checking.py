#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Container
from typing import Final

from cmk.utils.validatedstr import ValidatedString

__all__ = ["CheckPluginName", "CheckPluginNameStr", "Item"]

CheckPluginNameStr = str
Item = str | None


class CheckPluginName(ValidatedString):
    MANAGEMENT_PREFIX: Final = "mgmt_"

    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()

    def is_management_name(self) -> bool:
        return self._value.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> CheckPluginName:
        if self.is_management_name():
            return self
        return CheckPluginName(f"{self.MANAGEMENT_PREFIX}{self._value}")

    def create_basic_name(self) -> CheckPluginName:
        if self.is_management_name():
            return CheckPluginName(self._value[len(self.MANAGEMENT_PREFIX) :])
        return self
