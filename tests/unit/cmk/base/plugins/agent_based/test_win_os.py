#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import win_os
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> win_os.Section:
    return win_os.parse_win_os(
        [
            [
                "ZMUCVCS05",
                "Microsoft Windows Server 2008 R2 Standard",
                "6.1.7601",
                "64-bit",
                "1",
                "0",
                "20120531230239.000000+120",
            ]
        ]
    )


def test_inventory_win_os(section: win_os.Section) -> None:
    assert list(win_os.inventory_win_os(section)) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "Windows",
                "vendor": "Microsoft",
                "name": "Microsoft Windows Server 2008 R2 Standard",
                "kernel_version": "6.1.7601",
                "arch": "x86_64",
                "service_pack": "1.0",
                "install_date": 1338498159,
            },
        ),
    ]
