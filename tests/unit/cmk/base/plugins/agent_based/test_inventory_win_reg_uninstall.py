#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_win_reg_uninstall import (
    inventory_win_reg_uninstall,
    parse_win_reg_uninstall,
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
            ],
        ),
    ],
)
def test_inventory_win_reg_uninstall(monkeypatch, string_table, expected_result):
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert sort_inventory_result(
        inventory_win_reg_uninstall(parse_win_reg_uninstall(string_table))
    ) == sort_inventory_result(expected_result)
