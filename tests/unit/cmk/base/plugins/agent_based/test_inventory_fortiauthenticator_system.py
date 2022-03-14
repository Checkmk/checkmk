#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_fortiauthenticator_system import (
    inventory_fortiauthenticator_system,  # yapf: disable
)

from .utils_inventory import sort_inventory_result


def test_inventory_fortiauthenticator_system():
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
