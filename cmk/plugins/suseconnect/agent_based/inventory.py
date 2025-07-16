#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
)
from cmk.plugins.suseconnect.agent_based.agent_section import get_data, Section

_MAP: Final = (
    ("starts_at", "License Begin"),
    ("expires_at", "License Expiration"),
    ("regcode", "Registration Code"),
    ("status", "Registration Status"),
    ("subscription_status", "Subscription Status"),
    ("type", "Subscription Type"),
)


def inventory(section: Section) -> InventoryResult:
    if (data := get_data(section)) is None:
        return
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            description: value for key, description in _MAP if (value := data.get(key)) is not None
        },
    )


inventory_plugin_suseconnect = InventoryPlugin(
    name="suseconnect",
    inventory_function=inventory,
)
