#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_fortisandbox_software import (
    inventory_fortisandbox_software,
    parse_fortisandbox_software,
)

from .utils_inventory import sort_inventory_result

SECTION = [
    ("Tracer engine", "5.2.50534"),
    ("Rating engine", "2.4.20034"),
    ("System tools", "3.2.279"),
    ("Sniffer", "4.478"),
    ("Network alerts signature database", "14.613"),
    ("Android analytic engine", ""),
    ("Android rating engine", ""),
]


def test_parse_fortisandbox_software_inv() -> None:
    parsed = parse_fortisandbox_software(
        [
            ["5.2.50534", "2.4.20034", "3.2.279", "4.478", "14.613", "", ""],
        ]
    )
    assert parsed is not None
    assert list(parsed) == SECTION


def test_inventory_fortisandbox_software() -> None:
    assert sort_inventory_result(inventory_fortisandbox_software(SECTION)) == sort_inventory_result(
        [
            TableRow(
                path=["software", "applications", "fortinet", "fortisandbox"],
                key_columns={"name": "Tracer engine"},
                inventory_columns={
                    "version": "5.2.50534",
                },
            ),
            TableRow(
                path=["software", "applications", "fortinet", "fortisandbox"],
                key_columns={"name": "Rating engine"},
                inventory_columns={
                    "version": "2.4.20034",
                },
            ),
            TableRow(
                path=["software", "applications", "fortinet", "fortisandbox"],
                key_columns={"name": "System tools"},
                inventory_columns={
                    "version": "3.2.279",
                },
            ),
            TableRow(
                path=["software", "applications", "fortinet", "fortisandbox"],
                key_columns={"name": "Sniffer"},
                inventory_columns={
                    "version": "4.478",
                },
            ),
            TableRow(
                path=["software", "applications", "fortinet", "fortisandbox"],
                key_columns={"name": "Network alerts signature database"},
                inventory_columns={
                    "version": "14.613",
                },
            ),
        ]
    )
