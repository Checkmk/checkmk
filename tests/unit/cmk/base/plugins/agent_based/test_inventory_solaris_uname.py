#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.solaris_uname import (
    inventory_solaris_uname,
    parse_solaris_uname,
    Section,
)


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    return parse_solaris_uname(
        [
            ["System", "SunOS"],
            ["Node", "stickynode42"],
            ["Release", "5.10"],
            ["KernelID", "Generic_150401-41"],
            ["Machine", "i86pc"],
            ["BusType", "<unknown>"],
            ["Serial", "<unknown>"],
            ["Users", "<unknown>"],
            ["OEM#", "0"],
            ["Origin#", "1"],
            ["NumCPU", "64"],
        ]
    )


def test_inventory_solaris_uname(section: Section) -> None:
    assert list(inventory_solaris_uname(section)) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "vendor": "Oracle",
                "type": "SunOS",
                "version": "5.10",
                "name": "SunOS 5.10",
                "kernel_version": "Generic_150401-41",
                "hostname": "stickynode42",
            },
        ),
    ]
