#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based import cisco_fru_module_status


def test_parse() -> None:
    assert cisco_fru_module_status.parse(
        [
            [
                ["32", "9", "Fabric card module"],
                ["149", "3", "Nexus7700 C7706 (6 Slot) Chassis"],
                ["214", "5", "LinecardSlot-1"],
                ["406", "4", "Backplane"],
                ["470", "6", "PowerSupply-1"],
                ["534", "7", "Fan Module-1"],
                ["598", "1", "module-1 processor-1"],
                ["4950", "10", "Linecard-1 Port-1"],
            ],
            [
                ["32", "2"],
            ],
        ]
    ) == {
        "32": cisco_fru_module_status.Module(state="2", name="Fabric card module"),
    }


def test_parse_invalid_phyiscal_class() -> None:
    assert (
        cisco_fru_module_status.parse(
            [
                [
                    ["9", "3", "CHASSIS-1"],
                    ["10", "0", ""],
                    ["11", "7", "FAN-1"],
                    ["12", "0", ""],
                    ["13", "0", ""],
                    ["14", "0", ""],
                    ["15", "6", "PSU-1"],
                    ["16", "0", ""],
                    ["17", "1", "MEMORY-1"],
                    ["18", "0", ""],
                    ["19", "0", ""],
                    ["20", "0", ""],
                    ["21", "1", "SSD-1"],
                    ["22", "0", ""],
                    ["23", "12", "CPU-1"],
                    ["24", "0", ""],
                    ["25", "0", ""],
                ],
                [],
            ]
        )
        == {}
    )


def test_discover() -> None:
    assert list(
        cisco_fru_module_status.inventory_cisco_fru_module_status(
            {
                "32": cisco_fru_module_status.Module(state="2", name="Fabric card module"),
            }
        )
    ) == [
        Service(item="32"),
    ]


def test_check() -> None:
    assert list(
        cisco_fru_module_status.check_cisco_fru_module_status(
            item="32",
            section={
                "32": cisco_fru_module_status.Module(state="2", name="Fabric card module"),
            },
        )
    ) == [
        Result(state=State.OK, summary="[Fabric card module] Operational status: OK"),
    ]
