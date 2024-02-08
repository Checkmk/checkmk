#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable
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
        (
            [
                [
                    "0000",
                    "00",
                    "02.0 VGA compatible controller",
                    " Intel Corporation Device 9a49 (rev 01) (prog-if 00 [VGA controller])",
                ],
                ["Subsystem", " Dell Device 0a38"],
                ["Flags", " bus master, fast devsel, latency 0, IRQ 167"],
                ["Memory at 6054000000 (64-bit, non-prefetchable) [size=16M]"],
                ["Memory at 4000000000 (64-bit, prefetchable) [size=256M]"],
                ["I/O ports at 3000 [size=64]"],
                ["Expansion ROM at 000c0000 [virtual] [disabled] [size=128K]"],
                ["Capabilities", " <access denied>"],
                ["Kernel driver in use", " i915"],
                ["Kernel modules", " i915"],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "name": " Intel Corporation Device 9a49 (rev 01) (prog-if 00 [VGA controller])",
                    },
                    inventory_columns={
                        "subsystem": " Dell Device 0a38",
                        "driver": " i915",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_lnx_video(string_table: StringTable, expected_result: InventoryResult) -> None:
    assert list(inventory_lnx_video(parse_lnx_video(string_table))) == expected_result
