#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_lnx_packages import (
    inventory_lnx_packages,
    parse_lnx_packages,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["pacname4", "1.2.3", "amd64", "deb", "v5", "summary", "not-in-stalled"],
                ["pacname5", "1.2.3", "amd64", "deb", "v5", "summary", "installed"],
                ["pacname6", "1.2.3-4", "amd64", "deb", "v5", "summary", "installed"],
                ["pacname1", "1.2.3", "amd64", "deb", "summary", "not-in-stalled"],
                ["pacname2", "1.2.3", "amd64", "deb", "summary", "installed"],
                ["pacname3", "1.2.3-4", "amd64", "deb", "summary", "installed"],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "pacname2",
                    },
                    inventory_columns={
                        "version": "1.2.3",
                        "arch": "x86_64",
                        "package_type": "deb",
                        "summary": "summary",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "pacname3",
                    },
                    inventory_columns={
                        "version": "1.2.3",
                        "arch": "x86_64",
                        "package_type": "deb",
                        "summary": "summary",
                        "package_version": "4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "pacname5",
                    },
                    inventory_columns={
                        "version": "1.2.3",
                        "arch": "x86_64",
                        "package_type": "deb",
                        "summary": "summary",
                        "package_version": "v5",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "pacname6",
                    },
                    inventory_columns={
                        "version": "1.2.3",
                        "arch": "x86_64",
                        "package_type": "deb",
                        "summary": "summary",
                        "package_version": "v5",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_lnx_packages(string_table, expected_result):
    assert sort_inventory_result(
        inventory_lnx_packages(parse_lnx_packages(string_table))
    ) == sort_inventory_result(expected_result)
