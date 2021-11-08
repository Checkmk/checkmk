#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_win_wmi_updates import (
    inventory_win_wmi_updates,
    parse_win_wmi_updates,
)

_INSTALLED_DATE = 123.0


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["Node", "Description", "HotFixID", "InstalledOn"],
                ["S050MWSIZ001", "Update", "KB2849697-1", "20170523"],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "Windows Update KB2849697-1",
                    },
                    inventory_columns={
                        "version": "KB2849697-1",
                        "vendor": "Microsoft Update",
                        "install_date": _INSTALLED_DATE,
                        "package_type": "wmi",
                    },
                    status_columns={},
                ),
            ],
        ),
        (
            [
                ["Node", "Description", "HotFixID", "InstalledOn"],
                ["S050MWSIZ001", "Update", "KB2849697-2", "23-10-2013"],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "Windows Update KB2849697-2",
                    },
                    inventory_columns={
                        "version": "KB2849697-2",
                        "vendor": "Microsoft Update",
                        "install_date": _INSTALLED_DATE,
                        "package_type": "wmi",
                    },
                    status_columns={},
                ),
            ],
        ),
        (
            [
                ["Node", "Description", "HotFixID", "InstalledOn"],
                ["S050MWSIZ001", "Update", "KB2849697-3", "5/10/2017"],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "Windows Update KB2849697-3",
                    },
                    inventory_columns={
                        "version": "KB2849697-3",
                        "vendor": "Microsoft Update",
                        "install_date": _INSTALLED_DATE,
                        "package_type": "wmi",
                    },
                    status_columns={},
                ),
            ],
        ),
        (
            [
                ["Node", "Description", "HotFixID", "InstalledOn"],
                ["S050MWSIZ001", "Update", "KB2849697-4", "01ce83596afd20a7"],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "Windows Update KB2849697-4",
                    },
                    inventory_columns={
                        "version": "KB2849697-4",
                        "vendor": "Microsoft Update",
                        # time.mktime not used
                        "install_date": 13018585931.062492,
                        "package_type": "wmi",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_wmi_updates(monkeypatch, string_table, expected_result):
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert list(inventory_win_wmi_updates(parse_win_wmi_updates(string_table))) == expected_result
