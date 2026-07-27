#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.f5os_rseries.agent_based.inventory import (
    _extract_f5os_version,
    inventory_f5os_rseries,
    parse_f5os_rseries_inventory,
)
from cmk.plugins.f5os_rseries.lib.psu import parse_f5os_rseries_psu

# Walk from the reference r5800.
_INVENTORY_STRING_TABLE = [
    [["F5 rSeries-r5800 : Linux 3.10.0 : Appliance services version 1.8.3-23493"]],
    [["8.112.108.97.116.102.111.114.109", "r5800"]],
    [["8.112.108.97.116.102.111.114.109", "36", "72", "Intel(R) Xeon(R) Gold 6338N"]],
    [
        [
            "20.112.108.97.116.102.111.114.109.46.110.118.109.101.48.110.49",
            "SAMSUNG MZ1LB960HAJQ",
            "S436NA0N123456",
            "652.00GB",
        ]
    ],
]

# name, serial, model, currentIn, currentOut, voltageIn, voltageOut, temp1, powerIn, powerOut
_PSU_STRING_TABLE = [
    [
        "psu-1",
        "S92341RE0201",
        "PWR-0306-09",
        "1656",
        "28625",
        "230000",
        "11984",
        "360",
        "352000",
        "343000",
    ],
    ["psu-2", "S92341RE0923", "PWR-0306-09", "0", "0", "0", "1453", "360", "0", "0"],
]


@pytest.mark.parametrize(
    "sysdescr,expected",
    [
        ("F5 rSeries-r5800 : Linux : Appliance services version 1.8.3-23493", "1.8.3-23493"),
        ("no version string here", ""),
    ],
)
def test_extract_f5os_version(sysdescr: str, expected: str) -> None:
    assert _extract_f5os_version(sysdescr) == expected


def test_inventory_f5os_rseries() -> None:
    inv_section = parse_f5os_rseries_inventory(_INVENTORY_STRING_TABLE)
    assert inv_section is not None
    attrs = {
        tuple(a.path): a.inventory_attributes
        for a in inventory_f5os_rseries(inv_section, None)
        if isinstance(a, Attributes)
    }
    assert attrs[("hardware", "system")]["model"] == "r5800"
    assert attrs[("software", "os")]["version"] == "1.8.3-23493"
    assert attrs[("hardware", "cpu")]["cores"] == 36
    assert attrs[("hardware", "cpu")]["threads"] == 72
    assert attrs[("hardware", "storage")]["model"] == "SAMSUNG MZ1LB960HAJQ"


def test_inventory_f5os_rseries_includes_psu_rows() -> None:
    inv_section = parse_f5os_rseries_inventory(_INVENTORY_STRING_TABLE)
    psu_section = parse_f5os_rseries_psu(_PSU_STRING_TABLE)
    rows = [
        r for r in inventory_f5os_rseries(inv_section, psu_section) if not isinstance(r, Attributes)
    ]
    assert {r.key_columns["name"] for r in rows} == {"psu-1", "psu-2"}
