#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.inventory_fortimail_system import inventory_fortimail_system


def test_fortimail_serial_inventory() -> None:
    assert list(
        inventory_fortimail_system(
            {
                "model": "FortiMail-VM",
                "serial": "FEVM1234567890",
                "os": "v5.4,build719,180328 (5.4.5 GA)",
            },
        ),
    ) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "model": "FortiMail-VM",
                "serial": "FEVM1234567890",
            },
        ),
        Attributes(
            path=["software", "operating_system"],
            inventory_attributes={
                "version": "v5.4,build719,180328 (5.4.5 GA)",
            },
        ),
    ]
