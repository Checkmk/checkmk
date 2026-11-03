#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.juniper.agent_based.juniper_info import (
    inventorize_juniper_info,
    parse_juniper_info,
)


def test_inventorize_juniper_info_uses_the_current_hardware_system_keys() -> None:
    section = parse_juniper_info([["Juniper SRX300 Internet Router", "CV4716AF0123"]])
    assert section is not None

    assert list(inventorize_juniper_info(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "serial": "CV4716AF0123",
                "model": "Juniper SRX300 Internet Router",
            },
        )
    ]
