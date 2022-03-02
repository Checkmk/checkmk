#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_fortisandbox_system import inventory_fortisandbox_system

from .utils_inventory import sort_inventory_result


def test_inventory_fortisandbox_system():
    assert sort_inventory_result(
        inventory_fortisandbox_system(["v2.52-build0340 (GA)"])
    ) == sort_inventory_result(
        [
            Attributes(
                path=["software", "os"],
                inventory_attributes={
                    "Version": "v2.52-build0340 (GA)",
                },
            ),
        ]
    )
