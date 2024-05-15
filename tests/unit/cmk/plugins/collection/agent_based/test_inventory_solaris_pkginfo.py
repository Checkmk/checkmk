#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.collection.agent_based.inventory_solaris_pkginfo import (
    inventory_solaris_pkginfo,
    parse_solaris_pkginfo,
)

from .utils_inventory import sort_inventory_result

_INSTALLED_DATE = 123


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["PKGINST", "  SUNWzoneu"],  # PKGINST
                ["NAME", "  Solaris Zones (Usr)"],
                ["CATEGORY", "  system"],
                ["ARCH", "  i386"],
                ["VERSION", "  11.11,REV=2009.11.11"],
                ["BASEDIR", "  /"],
                ["VENDOR", "  Oracle Corporation"],
                ["DESC", "  Solaris Zones Configuration and Administration"],
                ["INSTDATE", "  Aug 20 2018 13", "11"],
                ["HOTLINE", "  Please contact your local service provider"],
                ["STATUS", "  completely installed"],
                ["PKGINST", "  SUNWzyd"],  # PKGINST
                ["NAME", "  ZyDAS ZD1211 USB 802.11b/g Wireless Driver"],
                ["CATEGORY", "  system"],
                ["ARCH", "  i386"],
                ["VERSION", "  11.11,REV=2009.11.11"],
                ["BASEDIR", "  /"],
                ["VENDOR", "  Oracle Corporation"],
                ["DESC", "  ZyDAS ZD1211 USB 802.11b/g Wireless Driver"],
                ["INSTDATE", "  Aug 20 2018 13", "11"],
                ["HOTLINE", "  Please contact your local service provider"],
                ["STATUS", "  completely installed"],
            ],
            [
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "SUNWzoneu - Solaris Zones (Usr)",
                    },
                    inventory_columns={
                        "package_type": "system",
                        "arch": "i386",
                        "version": "11.11,REV=2009.11.11",
                        "vendor": "Oracle Corporation",
                        "summary": "Solaris Zones Configuration and Administration",
                        "install_date": _INSTALLED_DATE,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "packages"],
                    key_columns={
                        "name": "SUNWzyd - ZyDAS ZD1211 USB 802.11b/g Wireless Driver",
                    },
                    inventory_columns={
                        "package_type": "system",
                        "arch": "i386",
                        "version": "11.11,REV=2009.11.11",
                        "vendor": "Oracle Corporation",
                        "summary": "ZyDAS ZD1211 USB 802.11b/g Wireless Driver",
                        "install_date": _INSTALLED_DATE,
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_solaris_pkginfo(
    monkeypatch: pytest.MonkeyPatch,
    string_table: StringTable,
    expected_result: InventoryResult,
) -> None:
    monkeypatch.setattr(time, "mktime", lambda s: _INSTALLED_DATE)
    assert sort_inventory_result(
        inventory_solaris_pkginfo(parse_solaris_pkginfo(string_table))
    ) == sort_inventory_result(expected_result)
