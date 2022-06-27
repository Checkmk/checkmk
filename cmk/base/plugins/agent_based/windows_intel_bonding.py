#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import bonding


def _get_real_adapter_name(bond: str, name: str) -> str:
    return name[len(f"TEAM : {bond} - ") :]


def parse_windows_intel_bonding(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> bonding.Section:
    lines = iter(string_table)
    bonds: dict[str, dict[str, str]] = {}
    adapters: dict[str, dict[str, str]] = {}
    adapter_names: dict[str, str] = {}

    try:
        # Get bond info
        line = next(lines)
        if line[0] != "###":
            while True:
                line = next(lines)
                if line[0] == "###":
                    break
                bond_caption = " ".join(line[:-2])
                bond_name, bond_mode = line[-2], line[-1]
                bonds[bond_name] = {"caption": bond_caption, "mode": bond_mode}

        # Get adapter info
        line = next(lines)
        if line[0] != "###":
            while True:
                line = next(lines)
                if line[0] == "###":
                    break
                adapter_function, adapter_status = line[0], line[1]
                adapter_bond = line[2].split(",")[-1].split("=")[1][1:-1]
                adapter = line[3].split(",")[1].split("=")[1][1:-1]
                adapters[adapter] = {
                    "function": adapter_function,
                    "status": adapter_status,
                    "bond": adapter_bond,
                }

        # Get adapter names
        line = next(lines)  # Skip header
        while True:
            line = next(lines)
            adapter_names[line[-1]] = " ".join(line[1:-1])

    except StopIteration:
        pass

    # Now convert to generic dict, also used by other bonding checks
    converted: dict[str, bonding.Bond] = {}
    map_adapter_status = {"0": "Unknown", "1": "up", "2": "up", "3": "down"}
    for bond, status in bonds.items():
        interfaces: dict[str, bonding.Interface] = {}
        bond_status = "down"
        converted[status["caption"]] = {}
        for adapter, adapter_info in adapters.items():
            if bond == adapter_info["bond"]:
                real_adapter_name = _get_real_adapter_name(
                    status["caption"], adapter_names[adapter]
                )
                if adapter_info["function"] == "1":
                    converted[status["caption"]]["primary"] = real_adapter_name
                if adapter_info["status"] == "1":
                    converted[status["caption"]]["active"] = real_adapter_name
                    bond_status = "up"
                interfaces[real_adapter_name] = {
                    "status": map_adapter_status.get(adapter_info["status"], "down"),
                }

        converted[status["caption"]].update(
            {
                "status": bond_status,
                "mode": status["mode"],
                "interfaces": interfaces,
            }
        )

    return converted


register.agent_section(
    name="windows_intel_bonding",
    parsed_section_name="bonding",
    parse_function=parse_windows_intel_bonding,
)
