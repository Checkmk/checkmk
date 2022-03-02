#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_aix_packages import (
    inventory_aix_packages,
    parse_aix_packages,
)

from .utils_inventory import sort_inventory_result

# Note: package_type is faked


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        ([], []),
        (
            [
                [
                    "#Package Name",
                    "Fileset",
                    "Level",
                    "State",
                    "PTF Id",
                    "Fix State",
                    "Type",
                    "Description",
                    "Destination Dir.",
                    "Uninstaller",
                    "Message Catalog",
                    "Message Set",
                    "Message Number",
                    "Parent",
                    "Automatic",
                    "EFIX Locked",
                    "Install Path",
                    "Build Date",
                ],
                [
                    "EMC",
                    "EMC.CLARiiON.aix.rte",
                    "6.0.0.3",
                    " ",
                    " ",
                    "C",
                    " ",
                    "EMC CLARiiON AIX Support Software",
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    "0",
                    "0",
                    "/",
                    "",
                ],
                [
                    "Java6.sdk",
                    "Java6.sdk",
                    "6.0.0.375",
                    " ",
                    " ",
                    "C",
                    "R",
                    "Java SDK 32-bit",
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    "0",
                    "0",
                    "/",
                    "",
                ],
                [
                    "ICU4C.rte",
                    "ICU4C.rte",
                    "7.1.2.0",
                    " ",
                    " ",
                    "C",
                    "TYPE",
                    "International Components for Unicode ",
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    " ",
                    "0",
                    "0",
                    "/",
                    "1241",
                ],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={"name": "EMC"},
                    inventory_columns={
                        "summary": "EMC CLARiiON AIX Support Software",
                        "version": "6.0.0.3",
                        "package_type": "aix",
                    },
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={"name": "ICU4C.rte"},
                    inventory_columns={
                        "summary": "International Components for Unicode",
                        "version": "7.1.2.0",
                        "package_type": "aix_type",
                    },
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={"name": "Java6.sdk"},
                    inventory_columns={
                        "summary": "Java SDK 32-bit",
                        "version": "6.0.0.375",
                        "package_type": "rpm",
                    },
                ),
            ],
        ),
    ],
)
def test_inv_aix_packages(raw_section, expected_result):
    assert sort_inventory_result(
        inventory_aix_packages(parse_aix_packages(raw_section))
    ) == sort_inventory_result(expected_result)
