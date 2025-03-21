#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.windows.agent_based.inventory_win_reg_uninstall import (
    inventory_win_reg_uninstall,
    parse_win_reg_uninstall,
)

_INSTALLED_DATE = 123


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "VMware Tools 2",
                    "VMware, Inc.",
                    "C:\\Program Files\\VMware\\VMware Tools\\",
                    "{123}",
                    "10.0.0.3000743",
                    "",
                    "20160930",
                    "1031",
                ],
                [
                    "VMware Tools 1",
                    "VMware, Inc.",
                    "C:\\Program Files\\VMware\\VMware Tools\\",
                    "{456}",
                    "10.0.0.3000743",
                    "",
                    "20160930",
                    "1031",
                ],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "VMware Tools 2",
                    },
                    inventory_columns={
                        "version": "10.0.0.3000743",
                        "vendor": "VMware, Inc.",
                        "summary": "VMware Tools 2",
                        "install_date": _INSTALLED_DATE,
                        "size": None,
                        "path": "C:\\Program Files\\VMware\\VMware Tools\\",
                        "language": "1031",
                        "package_type": "registry",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "VMware Tools 1",
                    },
                    inventory_columns={
                        "version": "10.0.0.3000743",
                        "vendor": "VMware, Inc.",
                        "summary": "VMware Tools 1",
                        "install_date": _INSTALLED_DATE,
                        "size": None,
                        "path": "C:\\Program Files\\VMware\\VMware Tools\\",
                        "language": "1031",
                        "package_type": "registry",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_reg_uninstall(
    monkeypatch: pytest.MonkeyPatch,
    string_table: StringTable,
    expected_result: InventoryResult,
) -> None:
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert (
        list(inventory_win_reg_uninstall(parse_win_reg_uninstall(string_table))) == expected_result
    )
