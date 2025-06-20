#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    Attributes,
    exists,
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
    HostLabel,
    HostLabelGenerator,
)
from cmk.plugins.lib.device_types import get_device_type_label


class SNMPExtendedInfoEntry(NamedTuple):
    idx: str
    name: str
    description: str
    software: str
    serial: str
    manufacturer: str
    model: str
    location: str


class SNMPExtendedInfo(NamedTuple):
    description: str  # First description is used for host labels
    serial: str | None  # Used for 'global' device Attributes
    model: str | None  # Used for 'global' device Attributes
    entities: Mapping[str, Sequence[SNMPExtendedInfoEntry]]


# Second entry is also used in the HW/SW path
_MAP_TYPE = {
    "1": ("Other", "others"),
    "2": ("Unknown", "unknowns"),
    "3": ("Chassis", "chassis"),
    "4": ("Backplane", "backplanes"),
    "5": ("Container", "containers"),
    "6": ("PSU", "psus"),
    "7": ("Fan", "fans"),
    "8": ("Sensor", "sensors"),
    "9": ("Module", "modules"),
    "10": ("Port", "ports"),
    "11": ("Stack", "stacks"),
}


Section = SNMPExtendedInfo


def parse_snmp_extended_info(string_table: StringTable) -> Section:
    parsed: dict[str, tuple[str, ...]] = {}
    count_parents = 0

    for (
        child,
        description,
        parent,
        child_type,
        name,
        software,
        serial,
        manufacturer,
        model,
    ) in string_table:
        if parent == "0":
            count_parents += 1

        if child_type in _MAP_TYPE:
            parsed.setdefault(
                child,
                (parent, description, child_type, name, software, serial, manufacturer, model),
            )
        else:
            parsed.setdefault(
                child, (parent, description, "2", name, software, serial, manufacturer, model)
            )

    parent_info_serial = None
    parent_info_model = None
    children_info_by_type: dict[str, list[SNMPExtendedInfoEntry]] = {}

    for index, (
        parent,
        description,
        entity_type,
        name,
        software,
        serial,
        manufacturer,
        model,
    ) in parsed.items():
        if count_parents == 1 and parent == "0":
            if serial:
                parent_info_serial = serial
            if model:
                parent_info_model = model

        elif entity_type != "10":
            if parsed.get(parent):
                location_info = (_MAP_TYPE[parsed[parent][2]][0], parent)
            elif parent == "0":
                location_info = ("Device", "0")
            else:
                location_info = ("Missing in ENTITY table", parent)

            children_info_by_type.setdefault(_MAP_TYPE[entity_type][1], []).append(
                SNMPExtendedInfoEntry(
                    idx=index,
                    name=name,
                    description=description,
                    software=software,
                    serial=serial,
                    manufacturer=manufacturer,
                    model=model,
                    location="%s (%s)" % location_info,
                )
            )

    return SNMPExtendedInfo(
        description=_get_first_description(string_table),
        serial=parent_info_serial,
        model=parent_info_model,
        entities=children_info_by_type,
    )


def _get_first_description(string_table: StringTable) -> str:
    try:
        return string_table[0][1]
    except IndexError:
        return ""


def host_label_snmp_extended_info(section: SNMPExtendedInfo) -> HostLabelGenerator:
    yield from get_device_type_label(section)
    if section.model:
        yield HostLabel(
            name="cmk/device_model",
            value=section.model,
        )


snmp_section_snmp_extended_info = SimpleSNMPSection(
    name="snmp_extended_info",
    parse_function=parse_snmp_extended_info,
    host_label_function=host_label_snmp_extended_info,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.47.1.1.1.1",
        oids=[
            OIDEnd(),
            "2",  # entPhysicalDescr
            "4",  # entPhysicalContainedIn
            "5",  # entPhysicalClass
            "7",  # entPhysicalName
            "10",  # entPhysicalSoftwareRev (NEW)
            "11",  # entPhysicalSerialNum
            "12",  # entPhysicalMfgName (NEW)
            "13",  # entPhysicalModelName
        ],
    ),
    detect=exists(".1.3.6.1.2.1.47.1.1.1.1.*"),
)


def inventory_snmp_extended_info(section: Section) -> InventoryResult:
    if section.serial is not None or section.model is not None:
        yield Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "serial": section.serial,
                "model": section.model,
            },
        )

    for child_type, children in section.entities.items():
        child_path = ["hardware", "components", child_type]
        for child in children:
            yield TableRow(
                path=child_path,
                key_columns={
                    "index": child.idx,
                    "name": child.name,
                },
                inventory_columns={
                    "description": child.description,
                    "software": child.software,
                    "serial": child.serial,
                    "manufacturer": child.manufacturer,
                    "model": child.model,
                    "location": child.location,
                },
                status_columns={},
            )


inventory_plugin_snmp_extended_info = InventoryPlugin(
    name="snmp_extended_info",
    inventory_function=inventory_snmp_extended_info,
)
