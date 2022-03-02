#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_win_exefiles import (
    inventory_win_exefiles,
    parse_win_exefiles,
)

from .utils_inventory import sort_inventory_result

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
                    },
                    inventory_columns={
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
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
                    },
                    inventory_columns={
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
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
                    },
                    inventory_columns={
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
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
                    },
                    inventory_columns={
                        "path": "C:\\Program Files (x86)\\ArcGIS\\License10.2\\bin",
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
    ],
)
def test_inventory_win_exefiles(monkeypatch, string_table, expected_result):
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert sort_inventory_result(
        inventory_win_exefiles(parse_win_exefiles(string_table))
    ) == sort_inventory_result(expected_result)
