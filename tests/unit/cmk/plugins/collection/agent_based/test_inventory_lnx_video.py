#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.collection.agent_based.inventory_lnx_video import (
    inventorize_lnx_video,
    parse_lnx_video,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param([], [], id="empty"),
        pytest.param(
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
                        "slot": "05:00.0",
                    },
                    inventory_columns={
                        "name": "Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])",
                        "subsystem": "Hightech Information System Ltd. Device 200b",
                        "driver": "fglrx_pci",
                    },
                    status_columns={},
                ),
            ],
            id="One graphics card",
        ),
        pytest.param(
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
                        "slot": "05:00.0",
                    },
                    inventory_columns={
                        "name": "Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])",
                        "subsystem": None,
                        "driver": None,
                    },
                    status_columns={},
                ),
            ],
            id="One graphics card with no subsystem and driver",
        ),
        pytest.param(
            [
                [
                    "0000",
                    "00",
                    "02.0 VGA compatible controller",
                    " Intel Corporation Device 9a49 (rev 01) (prog-if 00 [VGA controller])",
                ],
                ["Subsystem", " Dell Device 0a38"],
                ["Kernel driver in use", " i915"],
                ["Kernel modules", " i915"],
                [
                    "00",
                    "03.0 VGA compatible controller",
                    " Second graphics card",
                ],
                ["Subsystem", " Some subsystem"],
                ["Kernel driver in use", "Some driver"],
                ["Kernel modules", " i915"],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "slot": "0000:00:02.0",
                    },
                    inventory_columns={
                        "name": "Intel Corporation Device 9a49 (rev 01) (prog-if 00 [VGA controller])",
                        "subsystem": "Dell Device 0a38",
                        "driver": "i915",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "slot": "00:03.0",
                    },
                    inventory_columns={
                        "name": "Second graphics card",
                        "subsystem": "Some subsystem",
                        "driver": "Some driver",
                    },
                    status_columns={},
                ),
            ],
            id="Two graphics cards",
        ),
        pytest.param(
            [
                [
                    "00",
                    "08.0 VGA compatible controller",
                    " Microsoft Corporation Hyper-V virtual VGA (prog-if 00 [VGA controller])",
                ],
                ["Subsystem", " Hightech Information System Ltd. Device 200b"],
                ["Kernel driver in use", " hyperv_drm"],
                [
                    "00",
                    "08.1 VGA compatible controller",
                    " Microsoft Corporation Hyper-V virtual VGA (prog-if 00 [VGA controller])",
                ],
                ["Subsystem", " Hightech Information System Ltd. Device 200c"],
                ["Kernel driver in use", " hyperv_drm"],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "slot": "00:08.0",
                    },
                    inventory_columns={
                        "name": "Microsoft Corporation Hyper-V virtual VGA (prog-if 00 [VGA controller])",
                        "subsystem": "Hightech Information System Ltd. Device 200b",
                        "driver": "hyperv_drm",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "slot": "00:08.1",
                    },
                    inventory_columns={
                        "name": "Microsoft Corporation Hyper-V virtual VGA (prog-if 00 [VGA controller])",
                        "subsystem": "Hightech Information System Ltd. Device 200c",
                        "driver": "hyperv_drm",
                    },
                    status_columns={},
                ),
            ],
            id="Two identical graphics cards",
        ),
        pytest.param(
            [
                [
                    "0000",
                    "00",
                    "02.0 Something else here",
                    " Intel Corporation Device 9a49 (rev 01) (prog-if 00 [VGA controller])",
                ],
                ["Subsystem", " Dell Device 0a38"],
                ["Kernel driver in use", " i915"],
                ["Kernel modules", " i915"],
            ],
            [],
            id="Graphics card with no name",
        ),
    ],
)
def test_inventorize_lnx_video(string_table: StringTable, expected_result: InventoryResult) -> None:
    assert list(inventorize_lnx_video(parse_lnx_video(string_table))) == expected_result
