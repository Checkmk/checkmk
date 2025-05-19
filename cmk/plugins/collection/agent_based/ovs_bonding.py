#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib import bonding


class InvalidOvsBondingStringTable(Exception):
    """Raised when the structure of the string table is invalid."""


def parse_ovs_bonding(string_table: StringTable) -> bonding.Section:
    bonds: dict[str, dict[str, str]] = {}
    bonds_interfaces: dict[str, dict[str, bonding.Interface]] = {}
    current_bond: str | None = None
    last_interface: str | None = None

    for line in string_table:
        match line:
            case ["active slave"] if current_bond and last_interface:
                bonds[current_bond]["active"] = last_interface

            case [raw_bond] if raw_bond.startswith("[") and raw_bond.endswith("]"):
                current_bond = raw_bond.lstrip("[").rstrip("]")
                bonds[current_bond] = {}
                last_interface = None  # reset when handling new bond section

            case [key, value] if current_bond and key.startswith("slave"):
                _, eth = key.split()
                stripped_status = value.strip()
                status = "up" if stripped_status == "enabled" else stripped_status
                bonds_interfaces.setdefault(current_bond, {})[eth] = {"status": status}
                last_interface = eth

            case [key, value] if current_bond:
                bonds[current_bond][key] = value.strip()

            case _ if not current_bond:
                raise InvalidOvsBondingStringTable("Missing bond value.")

    parsed: dict[str, bonding.Bond] = {}

    for bond, status_map in bonds.items():
        if status_map.get("active") is None:
            continue

        is_running = any(itf.get("status") == "up" for itf in bonds_interfaces[bond].values())

        parsed[bond] = {
            "status": is_running and "up" or "down",
            "active": status_map["active"],
            "mode": status_map["bond_mode"],
            "interfaces": bonds_interfaces[bond],
        }

    return parsed


agent_section_ovs_bonding = AgentSection(
    name="ovs_bonding",
    parse_function=parse_ovs_bonding,
)
