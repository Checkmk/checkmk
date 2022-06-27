#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.fireeye_sys_status as fss
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, Result, Service, State


@pytest.fixture(name="section", scope="module")
def _get_section() -> fss.Section:
    section = fss.parse_fireeye_sys_status([["Good", "FireEye3400", "WWAECDD"]])
    assert section is not None
    return section


def test_parse_nothing() -> None:
    assert fss.parse_fireeye_sys_status([]) is None


def test_discovery(section: fss.Section) -> None:
    assert list(fss.discover_fireeye_sys_status(section)) == [Service()]


def test_check_ok(section: fss.Section) -> None:
    assert list(fss.check_fireeye_sys_status(section)) == [
        Result(state=State.OK, summary="Status: good"),
    ]


def test_inventory(section: fss.Section) -> None:
    assert list(fss.inventory_fireeye_sys_status(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "serial": "WWAECDD",
                "model": "FireEye3400",
            },
        )
    ]
