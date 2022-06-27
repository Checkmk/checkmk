#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_win_video import inventory_win_video, parse_win_video

from .utils_inventory import sort_inventory_result

_INSTALLED_DATE = 123


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["Name                 ", " VirtualBox Graphics Adapter"],
                ["Description          ", " VirtualBox Graphics Adapter"],
                ["Caption              ", " VirtualBox Graphics Adapter"],
                ["AdapterCompatibility ", " Oracle Corporation"],
                ["VideoProcessor       ", ""],
                ["DriverVersion        ", " 4.3.10.0"],
                ["DriverDate           ", " 20140326000000.000000-000"],
                ["MaxMemorySupported   ", ""],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "name": "VirtualBox Graphics Adapter",
                    },
                    inventory_columns={
                        "driver_version": "4.3.10.0",
                        "driver_date": _INSTALLED_DATE,
                        "graphic_memory": None,
                    },
                    status_columns={},
                ),
            ],
        ),
        (
            [
                ["Name                 ", " VirtualBox Graphics Adapter 2"],
                ["Description          ", " VirtualBox Graphics Adapter 2"],
                ["Caption              ", " VirtualBox Graphics Adapter 2"],
                ["AdapterCompatibility ", " Oracle Corporation"],
                ["VideoProcessor       ", ""],
                ["DriverVersion        ", " 4.3.10.0"],
                ["DriverDate           ", " 20140326000000.000000-000"],
                ["MaxMemorySupported   ", ""],
                ["Name                 ", " VirtualBox Graphics Adapter 1"],
                ["Description          ", " VirtualBox Graphics Adapter 1"],
                ["Caption              ", " VirtualBox Graphics Adapter 1"],
                ["AdapterCompatibility ", " Oracle Corporation"],
                ["VideoProcessor       ", ""],
                ["DriverVersion        ", " 4.3.10.0"],
                ["DriverDate           ", " 20140326000000.000000-000"],
                ["MaxMemorySupported   ", ""],
            ],
            [
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "name": "VirtualBox Graphics Adapter 1",
                    },
                    inventory_columns={
                        "driver_version": "4.3.10.0",
                        "driver_date": _INSTALLED_DATE,
                        "graphic_memory": None,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "video"],
                    key_columns={
                        "name": "VirtualBox Graphics Adapter 2",
                    },
                    inventory_columns={
                        "driver_version": "4.3.10.0",
                        "driver_date": _INSTALLED_DATE,
                        "graphic_memory": None,
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_video(monkeypatch, string_table, expected_result) -> None:
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert sort_inventory_result(
        inventory_win_video(parse_win_video(string_table))
    ) == sort_inventory_result(expected_result)
