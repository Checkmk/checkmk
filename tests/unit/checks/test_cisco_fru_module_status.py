#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks

check_name = "cisco_fru_module_status"

info = [
    [
        ["32", "Fabric card module", "9", "Fabric card module"],
        ["149", "Nexus7700 C7706 (6 Slot) Chassis", "3", "Nexus7700 C7706 (6 Slot) Chassis"],
        ["214", "LinecardSlot-1", "5", "LinecardSlot-1"],
        ["406", "Backplane", "4", "Backplane"],
        ["470", "N77-AC-3KW PS-1", "6", "PowerSupply-1"],
        ["534", "Fan Module-1", "7", "Fan Module-1"],
        ["598", "module-1 processor-1", "1", "module-1 processor-1"],
        ["4950", "Linecard-1 Port-1", "10", "Linecard-1 Port-1"],
    ],
    [
        ["32", "2"],
    ],
]


@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_cisco_fru_module_status() -> None:
    check = Check(check_name)
    assert check.run_parse(info) == {"32": {"name": "Fabric card module", "state": (0, "OK")}}
