#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.inventory_fortiauthenticator_system import (
    inventory_fortiauthenticator_system,  # fmt: off
)

from .utils_inventory import sort_inventory_result


def test_inventory_fortiauthenticator_system() -> None:
    assert sort_inventory_result(
        inventory_fortiauthenticator_system(
            {
                "model": "FACVM",
                "serial": "FAC-VMTM18000123",
            }
        )
    ) == sort_inventory_result(
        [
            Attributes(
                path=["hardware", "system"],
                inventory_attributes={
                    "Model": "FACVM",
                    "Serial number": "FAC-VMTM18000123",
                },
            ),
        ]
    )
