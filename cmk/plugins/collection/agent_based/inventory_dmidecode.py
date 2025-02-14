#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections import Counter
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

Section = list[tuple[str, StringTable]]


def parse_dmidecode(string_table: StringTable) -> Section:
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

    return subsections


agent_section_dmidecode = AgentSection(
    name="dmidecode",
    parse_function=parse_dmidecode,
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


def inventory_dmidecode(section: Section) -> InventoryResult:
    # There will be "Physical Memory Array" sections, each followed
    # by multiple "Memory Device" sections. Keep track of which belongs where:
    counter: Counter[Literal["physical_memory_array", "memory_device"]] = Counter()
    for title, lines in section:
        match title:
            case "BIOS Information":
                bios_information = _parse_bios_information(lines)
                yield Attributes(
                    path=["software", "bios"],
                    inventory_attributes={
                        "vendor": bios_information.vendor,
                        "version": bios_information.version,
                        "date": bios_information.release_date,
                        "revision": bios_information.bios_revision,
                        "firmware": bios_information.firmware_revision,
                    },
                )
            case "System Information":
                system_information = _parse_system_information(lines)
                yield Attributes(
                    path=["hardware", "system"],
                    inventory_attributes={
                        "manufacturer": system_information.manufacturer,
                        "product": system_information.product_name,
                        "version": system_information.version,
                        "serial": system_information.serial_number,
                        "uuid": system_information.uuid,
                        "family": system_information.family,
                    },
                )
            case "Chassis Information":
                chassis_information = _parse_chassis_information(lines)
                yield Attributes(
                    path=["hardware", "chassis"],
                    inventory_attributes={
                        "manufacturer": chassis_information.manufacturer,
                        "type": chassis_information.type,
                    },
                )
            case "Processor Information":
                processor_information = _parse_processor_information(lines)
                if processor_information.status != "Unpopulated":
                    # Note: This node is also being filled by lnx_cpuinfo
                    yield Attributes(
                        path=["hardware", "cpu"],
                        inventory_attributes={
                            "vendor": _map_vendor(processor_information.manufacturer),
                            "max_speed": processor_information.max_speed,
                            "voltage": processor_information.voltage,
                            "status": processor_information.status,
                        },
                    )
            case "Physical Memory Array":
                physical_memory_array = _parse_physical_memory_array(lines, counter)
                yield Attributes(
                    path=[
                        "hardware",
                        "memory",
                        "arrays",
                        str(physical_memory_array.index),
                    ],
                    inventory_attributes={
                        "location": physical_memory_array.location,
                        "use": physical_memory_array.use,
                        "error_correction": physical_memory_array.error_correction_type,
                        "maximum_capacity": physical_memory_array.maximum_capacity,
                    },
                )
            case "Memory Device":
                memory_device = _parse_memory_device(lines, counter)
                if memory_device.size is not None:
                    yield TableRow(
                        path=[
                            "hardware",
                            "memory",
                            "arrays",
                            str(memory_device.physical_memory_array),
                            "devices",
                        ],
                        key_columns={
                            "index": memory_device.index,
                            "set": memory_device.set,  # None
                        },
                        inventory_columns={
                            "total_width": memory_device.total_width,  # 64 bits
                            "data_width": memory_device.data_width,  # 64 bits
                            "form_factor": memory_device.form_factor,  # SODIMM
                            "locator": memory_device.locator,  # PROC 1 DIMM 2
                            "bank_locator": memory_device.bank_locator,  # Bank 2/3
                            "type": memory_device.type,  # DDR2
                            "type_detail": memory_device.type_detail,  # Synchronous
                            "manufacturer": memory_device.manufacturer,  # Not Specified
                            "serial": memory_device.serial_number,  # Not Specified
                            "asset_tag": memory_device.asset_tag,  # Not Specified
                            "part_number": memory_device.part_number,  # Not Specified
                            "speed": memory_device.speed,  # 667 MHz
                            "size": memory_device.size,  # 2048 MB
                        },
                    )


inventory_plugin_dmidecode = InventoryPlugin(
    name="dmidecode",
    inventory_function=inventory_dmidecode,
)
