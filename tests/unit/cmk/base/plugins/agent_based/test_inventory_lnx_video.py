#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_lnx_video import inventory_lnx_video, parse_lnx_video


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "05",
                    "00.0 VGA compatible controller",
                    "Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])",
                ],
                ["Subsystem", "Hightech Information System Ltd. Device 200b"],
                ["Kernel driver in use", "fglrx_pci"],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "name": "Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])",
                    },
                    inventory_columns={
                        "subsystem": "Hightech Information System Ltd. Device 200b",
                        "driver": "fglrx_pci",
                    },
                    status_columns={},
                ),
            ],
        ),
        (
            [
                [
                    "05",
                    "00.0 VGA compatible controller",
                    "Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])",
                ],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "name": "Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])",
                    },
                    inventory_columns={
                        "subsystem": None,
                        "driver": None,
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_lnx_video(string_table, expected_result) -> None:
    assert list(inventory_lnx_video(parse_lnx_video(string_table))) == expected_result
