#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.windows.agent_based.inventory_win_exefiles import (
    inventory_win_exefiles,
    parse_win_exefiles,
)

_INSTALLED_DATE = 123


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin\\ARCGIS.exe",
                    "28.05.2013 19:17:22",
                    "1662840",
                    "ARCGIS daemon",
                    "",
                    "",
                ]
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "ARCGIS.exe",
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
                    },
                    inventory_columns={
                        "package_type": "exe",
                        "install_date": _INSTALLED_DATE,
                        "size": 1662840,
                        "version": "",
                        "summary": "ARCGIS daemon",
                        "vendor": "",
                    },
                    status_columns={},
                )
            ],
        ),
        (
            [
                [
                    "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin\\ARCGIS.exe",
                    "05/28/2013 1:17:22 AM",
                    "1662840",
                    "ARCGIS daemon",
                    "",
                    "",
                ]
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "ARCGIS.exe",
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
                    },
                    inventory_columns={
                        "package_type": "exe",
                        "install_date": _INSTALLED_DATE,
                        "size": 1662840,
                        "version": "",
                        "summary": "ARCGIS daemon",
                        "vendor": "",
                    },
                    status_columns={},
                )
            ],
        ),
        (
            [
                [
                    "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin\\ARCGIS.exe",
                    "05/28/2013 1:17:22 PM",
                    "1662840",
                    "ARCGIS daemon",
                    "",
                    "",
                ]
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "ARCGIS.exe",
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
                    },
                    inventory_columns={
                        "package_type": "exe",
                        "install_date": _INSTALLED_DATE,
                        "size": 1662840,
                        "version": "",
                        "summary": "ARCGIS daemon",
                        "vendor": "",
                    },
                    status_columns={},
                )
            ],
        ),
        (
            [
                [
                    "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin\\ARCGIS.exe",
                    "05/28/2013 19:17:22",
                    "1662840",
                    "ARCGIS daemon",
                    "",
                    "",
                ]
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "ARCGIS.exe",
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
                    },
                    inventory_columns={
                        "package_type": "exe",
                        "install_date": _INSTALLED_DATE,
                        "size": 1662840,
                        "version": "",
                        "summary": "ARCGIS daemon",
                        "vendor": "",
                    },
                    status_columns={},
                )
            ],
        ),
        (
            [
                [
                    "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin\\ARCGIS.exe",
                    "05/28/2013 19:17:22",
                    "1662840",
                    "ARCGIS daemon",
                    "",
                    "",
                ],
                [
                    "C:\\Program Files (x86)\\ArcGIS\\License10.5\\bin\\ARCGIS.exe",
                    "05/28/2013 19:17:22",
                    "1662840",
                    "ARCGIS daemon",
                    "",
                    "",
                ],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "ARCGIS.exe",
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
                    },
                    inventory_columns={
                        "package_type": "exe",
                        "install_date": _INSTALLED_DATE,
                        "size": 1662840,
                        "version": "",
                        "summary": "ARCGIS daemon",
                        "vendor": "",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "ARCGIS.exe",
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.5\\bin",
                    },
                    inventory_columns={
                        "package_type": "exe",
                        "install_date": _INSTALLED_DATE,
                        "size": 1662840,
                        "version": "",
                        "summary": "ARCGIS daemon",
                        "vendor": "",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_exefiles(
    monkeypatch: pytest.MonkeyPatch,
    string_table: StringTable,
    expected_result: InventoryResult,
) -> None:
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert list(inventory_win_exefiles(parse_win_exefiles(string_table))) == expected_result
