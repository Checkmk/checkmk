#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, Result, Service, State
from cmk.base.plugins.agent_based.snmp_info import (
    check_snmp_info,
    discover_snmp_info,
    inventory_snmp_info,
    parse_snmp_info,
    SNMPInfo,
)


def test_parse_function_removes_newlines() -> None:
    assert parse_snmp_info(
        [
            [
                "KONICA MINOLTA bizhub C451\n",
                "0.1.2.3.4.5.6.7.8.9",
                "R.\nHantzsch",
                "Bizhub C451\r\n1.OG",
                "1.OG / Raum 1.08",
            ]
        ]
    ) == SNMPInfo(
        description="KONICA MINOLTA bizhub C451",
        object_id="0.1.2.3.4.5.6.7.8.9",
        contact="R. Hantzsch",
        name="Bizhub C451 1.OG",
        location="1.OG / Raum 1.08",
    )


@pytest.fixture(name="section", scope="module")
def _get_section() -> SNMPInfo:
    section = parse_snmp_info(
        [
            [
                "This is a cisco device, Version 1.2.3",
                ".1.3.6.1.4.1.25597.1",
                "Horst",
                "Kevin",
                "Über den Wolken",
            ],
        ]
    )
    assert section
    return section


def test_discover_snmp_info(section: SNMPInfo) -> None:
    assert list(discover_snmp_info(section)) == [Service()]


def test_check_snmp_info(section: SNMPInfo) -> None:
    assert list(check_snmp_info(section)) == [
        Result(
            state=State.OK,
            summary="This is a cisco device, Version 1.2.3, Kevin, Über den Wolken, Horst",
        ),
    ]


def test_inventory_snmp_info(section: SNMPInfo) -> None:
    assert list(inventory_snmp_info(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "product": "This is a cisco device, Version 1.2.3",
            },
        ),
        Attributes(
            path=["software", "configuration", "snmp_info"],
            inventory_attributes={
                "contact": "Horst",
                "name": "Kevin",
                "location": "Über den Wolken",
            },
        ),
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "This is a cisco device",
                "version": "1.2.3",
            },
        ),
    ]
