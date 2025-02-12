#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)


@dataclass(frozen=True, kw_only=True)
class BIOSInformation:
    vendor: str
    version: str
    release_date: float | None
    bios_revision: str
    firmware_revision: str


def _parse_date(value: str) -> float | None:
    try:
        return time.mktime(time.strptime(value, "%m/%d/%Y"))
    except ValueError:
        return None


def _parse_bios_information(lines: list[list[str]]) -> BIOSInformation:
    vendor = ""
    version = ""
    release_date = None
    bios_revision = ""
    firmware_revision = ""
    for name, raw_value, *_rest in lines:
        if raw_value == "Not Specified":
            continue
        match name:
            case "Vendor":
                vendor = raw_value
            case "Version":
                version = raw_value
            case "Release Date":
                release_date = _parse_date(raw_value)
            case "BIOS Revision":
                bios_revision = raw_value
            case "Firmware Revision":
                firmware_revision = raw_value
    return BIOSInformation(
        vendor=vendor,
        version=version,
        release_date=release_date,
        bios_revision=bios_revision,
        firmware_revision=firmware_revision,
    )


@dataclass(frozen=True, kw_only=True)
class SystemInformation:
    manufacturer: str
    product_name: str
    version: str
    serial_number: str
    uuid: str
    family: str


def _parse_system_information(lines: list[list[str]]) -> SystemInformation:
    manufacturer = ""
    product_name = ""
    version = ""
    serial_number = ""
    uuid = ""
    family = ""
    for name, raw_value, *_rest in lines:
        if raw_value == "Not Specified":
            continue
        match name:
            case "Manufacturer":
                manufacturer = raw_value
            case "Product Name":
                product_name = raw_value
            case "Version":
                version = raw_value
            case "Serial Number":
                serial_number = raw_value
            case "UUID":
                uuid = raw_value
            case "Family":
                family = raw_value
    return SystemInformation(
        manufacturer=manufacturer,
        product_name=product_name,
        version=version,
        serial_number=serial_number,
        uuid=uuid,
        family=family,
    )


@dataclass(frozen=True, kw_only=True)
class ChassisInformation:
    manufacturer: str
    type: str


def _parse_chassis_information(lines: list[list[str]]) -> ChassisInformation:
    manufacturer = ""
    type_ = ""
    for name, raw_value, *_rest in lines:
        if raw_value == "Not Specified":
            continue
        match name:
            case "Manufacturer":
                manufacturer = raw_value
            case "Type":
                type_ = raw_value
    return ChassisInformation(
        manufacturer=manufacturer,
        type=type_,
    )


@dataclass(frozen=True, kw_only=True)
class ProcessorInformation:
    manufacturer: str
    max_speed: float | None
    voltage: float | None
    status: str


def _parse_speed(v: str) -> float | None:  # into Hz (float)
    if not v or v == "Unknown":
        return None

    parts = v.split()
    if parts[1] == "GHz":
        return float(parts[0]) * 1000000000.0
    if parts[1] == "MHz":
        return float(parts[0]) * 1000000.0
    if parts[1] == "kHz":
        return float(parts[0]) * 1000.0
    if parts[1] == "Hz":
        return float(parts[0])
    return None


def _parse_voltage(v: str) -> float | None:
    if not v or v == "Unknown":
        return None

    parts = v.split()
    return float(parts[0])


def _parse_processor_information(lines: list[list[str]]) -> ProcessorInformation:
    manufacturer = ""
    max_speed: float | None = None
    voltage: float | None = None
    status = ""
    for name, raw_value, *_rest in lines:
        if raw_value == "Not Specified":
            continue
        match name:
            case "Manufacturer":
                manufacturer = raw_value
            case "Max Speed":
                max_speed = _parse_speed(raw_value)
            case "Voltage":
                voltage = _parse_voltage(raw_value)
            case "Status":
                status = raw_value
    return ProcessorInformation(
        manufacturer=manufacturer,
        max_speed=max_speed,
        voltage=voltage,
        status=status,
    )


def _map_vendor(manufacturer: str) -> str:
    return {
        "GenuineIntel": "intel",
        "Intel(R) Corporation": "intel",
        "AuthenticAMD": "amd",
    }.get(manufacturer, manufacturer)


@dataclass(frozen=True, kw_only=True)
class PhysicalMemoryArray:
    index: int
    location: str
    use: str
    error_correction_type: str
    maximum_capacity: float | None


def _parse_size(v: str) -> float | None:  # into Bytes (int)
    if not v or v == "Unknown":
        return None

    parts = v.split()
    if parts[1].lower() == "tb":
        return int(parts[0]) * 1024 * 1024 * 1024 * 1024
    if parts[1].lower() == "gb":
        return int(parts[0]) * 1024 * 1024 * 1024
    if parts[1].lower() == "mb":
        return int(parts[0]) * 1024 * 1024
    if parts[1].lower() == "kb":
        return int(parts[0]) * 1024
    return int(parts[0])


def _parse_physical_memory_array(
    lines: list[list[str]],
    counter: Counter[Literal["physical_memory_array", "memory_device"]],
) -> PhysicalMemoryArray:
    location = ""
    use = ""
    error_correction_type = ""
    maximum_capacity: float | None = None
    for name, raw_value, *_rest in lines:
        if raw_value == "Not Specified":
            continue
        match name:
            case "Location":
                location = raw_value
            case "Use":
                use = raw_value
            case "Error Correction Type":
                error_correction_type = raw_value
            case "Maximum Capacity":
                maximum_capacity = _parse_size(raw_value)
    counter.update({"physical_memory_array": 1})
    return PhysicalMemoryArray(
        index=counter["physical_memory_array"],
        location=location,
        use=use,
        error_correction_type=error_correction_type,
        maximum_capacity=maximum_capacity,
    )


@dataclass(frozen=True, kw_only=True)
class MemoryDevice:
    physical_memory_array: int
    index: int
    total_width: str
    data_width: str
    form_factor: str
    set: str
    locator: str
    bank_locator: str
    type: str
    type_detail: str
    manufacturer: str
    serial_number: str
    asset_tag: str
    part_number: str
    speed: float | None
    size: float | None


def _parse_memory_device(
    lines: list[list[str]],
    counter: Counter[Literal["physical_memory_array", "memory_device"]],
) -> MemoryDevice:
    total_width = ""
    data_width = ""
    form_factor = ""
    set_ = ""
    locator = ""
    bank_locator = ""
    type_ = ""
    type_detail = ""
    manufacturer = ""
    serial_number = ""
    asset_tag = ""
    part_number = ""
    speed: float | None = None
    size: float | None = None
    for name, raw_value, *_rest in lines:
        if raw_value == "Not Specified":
            continue
        match name:
            case "Total Width":
                total_width = raw_value
            case "Data Width":
                data_width = raw_value
            case "Form Factor":
                form_factor = raw_value
            case "Set":
                set_ = raw_value
            case "Locator":
                locator = raw_value
            case "Bank Locator":
                bank_locator = raw_value
            case "Type":
                type_ = raw_value
            case "Type Detail":
                type_detail = raw_value
            case "Manufacturer":
                manufacturer = raw_value
            case "Serial Number":
                serial_number = raw_value
            case "Asset Tag":
                asset_tag = raw_value
            case "Part Number":
                part_number = raw_value
            case "Speed":
                speed = _parse_speed(raw_value)
            case "Size":
                if raw_value != "No Module Installed":
                    size = _parse_size(raw_value)
    counter.update({"memory_device": 1})
    return MemoryDevice(
        physical_memory_array=counter["physical_memory_array"],
        index=counter["memory_device"],
        total_width=total_width,
        data_width=data_width,
        form_factor=form_factor,
        set=set_,
        locator=locator,
        bank_locator=bank_locator,
        type=type_,
        type_detail=type_detail,
        manufacturer=manufacturer,
        serial_number=serial_number,
        asset_tag=asset_tag,
        part_number=part_number,
        speed=speed,
        size=size,
    )


def parse_dmidecode(
    string_table: StringTable,
) -> Sequence[
    BIOSInformation
    | SystemInformation
    | ChassisInformation
    | ProcessorInformation
    | PhysicalMemoryArray
    | MemoryDevice
]:
    """Parse the output of `dmidecode -q | sed 's/\t/:/g'` with sep(58)
    Note: on Linux \t is replaced by : and then the split is done by :.
    On Windows the \t comes 1:1 and no splitting is being done.
    So we need to split manually here.
    """
    # We cannot use a dict here, we may have multiple
    # subsections with the same title and the order matters!
    subsections = []
    current_lines: StringTable = []  # these will not be used
    for line in string_table:
        # Windows plug-in keeps tabs and has no separator
        if len(line) == 1:
            parts = line[0].replace("\t", ":").split(":")
            line = [x.strip() for x in parts]

        if len(line) == 1:
            current_lines = []
            subsections.append((line[0], current_lines))
        else:
            current_lines.append([w.strip() for w in line[1:]])

    # There will be "Physical Memory Array" sections, each followed
    # by multiple "Memory Device" sections. Keep track of which belongs where:
    entities: list[
        BIOSInformation
        | SystemInformation
        | ChassisInformation
        | ProcessorInformation
        | PhysicalMemoryArray
        | MemoryDevice
    ] = []
    counter: Counter[Literal["physical_memory_array", "memory_device"]] = Counter()
    for title, lines in subsections:
        match title:
            case "BIOS Information":
                entities.append(_parse_bios_information(lines))
            case "System Information":
                entities.append(_parse_system_information(lines))
            case "Chassis Information":
                entities.append(_parse_chassis_information(lines))
            case "Processor Information":
                entities.append(_parse_processor_information(lines))
            case "Physical Memory Array":
                entities.append(_parse_physical_memory_array(lines, counter))
            case "Memory Device":
                entities.append(_parse_memory_device(lines, counter))
    return entities


agent_section_dmidecode = AgentSection(
    name="dmidecode",
    parse_function=parse_dmidecode,
)


def inventory_dmidecode(
    section: Sequence[
        BIOSInformation
        | SystemInformation
        | ChassisInformation
        | ProcessorInformation
        | PhysicalMemoryArray
        | MemoryDevice
    ],
) -> InventoryResult:
    for entity in section:
        match entity:
            case BIOSInformation():
                yield Attributes(
                    path=["software", "bios"],
                    inventory_attributes={
                        "vendor": entity.vendor,
                        "version": entity.version,
                        "date": entity.release_date,
                        "revision": entity.bios_revision,
                        "firmware": entity.firmware_revision,
                    },
                )
            case SystemInformation():
                yield Attributes(
                    path=["hardware", "system"],
                    inventory_attributes={
                        "manufacturer": entity.manufacturer,
                        "product": entity.product_name,
                        "version": entity.version,
                        "serial": entity.serial_number,
                        "uuid": entity.uuid,
                        "family": entity.family,
                    },
                )
            case ChassisInformation():
                yield Attributes(
                    path=["hardware", "chassis"],
                    inventory_attributes={
                        "manufacturer": entity.manufacturer,
                        "type": entity.type,
                    },
                )
            case ProcessorInformation():
                if entity.status != "Unpopulated":
                    # Note: This node is also being filled by lnx_cpuinfo
                    yield Attributes(
                        path=["hardware", "cpu"],
                        inventory_attributes={
                            "vendor": _map_vendor(entity.manufacturer),
                            "max_speed": entity.max_speed,
                            "voltage": entity.voltage,
                            "status": entity.status,
                        },
                    )
            case PhysicalMemoryArray():
                yield Attributes(
                    path=[
                        "hardware",
                        "memory",
                        "arrays",
                        str(entity.index),
                    ],
                    inventory_attributes={
                        "location": entity.location,
                        "use": entity.use,
                        "error_correction": entity.error_correction_type,
                        "maximum_capacity": entity.maximum_capacity,
                    },
                )
            case MemoryDevice():
                if entity.size is not None:
                    yield TableRow(
                        path=[
                            "hardware",
                            "memory",
                            "arrays",
                            str(entity.physical_memory_array),
                            "devices",
                        ],
                        key_columns={
                            "index": entity.index,
                            "set": entity.set,  # None
                        },
                        inventory_columns={
                            "total_width": entity.total_width,  # 64 bits
                            "data_width": entity.data_width,  # 64 bits
                            "form_factor": entity.form_factor,  # SODIMM
                            "locator": entity.locator,  # PROC 1 DIMM 2
                            "bank_locator": entity.bank_locator,  # Bank 2/3
                            "type": entity.type,  # DDR2
                            "type_detail": entity.type_detail,  # Synchronous
                            "manufacturer": entity.manufacturer,  # Not Specified
                            "serial": entity.serial_number,  # Not Specified
                            "asset_tag": entity.asset_tag,  # Not Specified
                            "part_number": entity.part_number,  # Not Specified
                            "speed": entity.speed,  # 667 MHz
                            "size": entity.size,  # 2048 MB
                        },
                    )


inventory_plugin_dmidecode = InventoryPlugin(
    name="dmidecode",
    inventory_function=inventory_dmidecode,
)
