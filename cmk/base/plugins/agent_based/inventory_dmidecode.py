#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Callable, Dict, Generator, List, Mapping, Optional, Tuple, Union

from .agent_based_api.v1 import Attributes, register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = List[Tuple[str, StringTable]]

Converter = Union[str, Tuple[str, Callable[[str], Union[str, float, None]]]]


def parse_dmidecode(string_table: StringTable) -> Section:
    """Parse the output of `dmidecode -q | sed 's/\t/:/g'` with sep(58)

    This is a *massively* reduced example:

        >>> from pprint import pprint
        >>> string_table = [line.split(':') for line in [
        ...     'Processor Information',
        ...     ':Type: Central Processor',
        ...     ':Family: Core i7',
        ...     ':Manufacturer: Intel(R) Corporation',
        ...     ':ID: 61 06 04 00 FF FB EB BF',
        ...     ':Flags:',
        ...     '::FPU (Floating-point unit on-chip)',
        ...     '::VME (Virtual mode extension)',
        ...     '::DE (Debugging extension)',
        ...     '',
        ...     'Chassis Information',
        ...     ':Manufacturer: Apple Inc.',
        ...     ':Type: Laptop',
        ...     '',
        ...     'Onboard Device',
        ...     ':Reference Designation: Integrated Video Controller',
        ...     ':Type: Video',
        ...     ':Status: Enabled',
        ...     ':Type Instance: 1',
        ...     ':Bus Address: 0000:00:00.0',
        ...     '',
        ...     'Physical Memory Array',
        ...     ':Location: System Board Or Motherboard',
        ...     ':Number Of Devices: 2',
        ...     '',
        ...     'Memory Device',
        ...     ':Bank Locator: BANK 0',
        ...     '',
        ...     'Memory Device',
        ...     ':Bank Locator: BANK 1',
        ... ] if line]
        >>> pprint(parse_dmidecode(string_table))
        [('Processor Information',
          [['Type', 'Central Processor'],
           ['Family', 'Core i7'],
           ['Manufacturer', 'Intel(R) Corporation'],
           ['ID', '61 06 04 00 FF FB EB BF'],
           ['Flags', ''],
           ['', 'FPU (Floating-point unit on-chip)'],
           ['', 'VME (Virtual mode extension)'],
           ['', 'DE (Debugging extension)']]),
         ('Chassis Information', [['Manufacturer', 'Apple Inc.'], ['Type', 'Laptop']]),
         ('Onboard Device',
          [['Reference Designation', 'Integrated Video Controller'],
           ['Type', 'Video'],
           ['Status', 'Enabled'],
           ['Type Instance', '1'],
           ['Bus Address', '0000', '00', '00.0']]),
         ('Physical Memory Array',
          [['Location', 'System Board Or Motherboard'], ['Number Of Devices', '2']]),
         ('Memory Device', [['Bank Locator', 'BANK 0']]),
         ('Memory Device', [['Bank Locator', 'BANK 1']])]


    Note: on Linux \t is replaced by : and then the split is done by :.
    On Windows the \t comes 1:1 and no splitting is being done.
    So we need to split manually here.
    """
    # We cannot use a dict here, we may have multiple
    # subsections with the same title and the order matters!
    subsections = []
    current_lines: StringTable = []  # these will not be used
    for line in string_table:
        # Windows plugin keeps tabs and has no separator
        if len(line) == 1:
            parts = line[0].replace("\t", ":").split(":")
            line = [x.strip() for x in parts]

        if len(line) == 1:
            current_lines = []
            subsections.append((line[0], current_lines))
        else:
            current_lines.append([w.strip() for w in line[1:]])

    return subsections


register.agent_section(
    name="dmidecode",
    parse_function=parse_dmidecode,
)


def inventory_dmidecode(section: Section) -> InventoryResult:
    # There will be "Physical Memory Array" sections, each followed
    # by multiple "Memory Device" sections. Keep track of which belongs where:
    memory_array_number = 0
    for title, lines in section:
        memory_array_number += title == "Physical Memory Array"
        yield from _dispatch_subsection(title, lines, memory_array_number)


def _dispatch_subsection(
    title: str,
    lines: List[List[str]],
    memory_array_number: int,
) -> InventoryResult:
    if title == "BIOS Information":
        yield _make_inventory_bios(lines)
        return

    if title == "System Information":
        yield _make_inventory_system(lines)
        return

    if title == "Chassis Information":
        yield _make_inventory_chassis(lines)
        return

    if title == "Processor Information":
        yield from _make_inventory_processor(lines)
        return

    if title == "Physical Memory Array":
        yield _make_inventory_physical_mem_array(lines, memory_array_number)
        return

    if title == "Memory Device":
        yield from _make_inventory_mem_device(lines, memory_array_number)
        return


def _make_inventory_bios(lines: List[List[str]]) -> Attributes:
    return Attributes(
        path=["software", "bios"],
        inventory_attributes=_make_dict(
            lines,
            {
                "Vendor": "vendor",
                "Version": "version",
                "Release Date": ("date", _parse_date),
                "BIOS Revision": "revision",
                "Firmware Revision": "firmware",
            },
        ),
    )


def _make_inventory_system(lines: List[List[str]]) -> Attributes:
    return Attributes(
        path=["hardware", "system"],
        inventory_attributes=_make_dict(
            lines,
            {
                "Manufacturer": "manufacturer",
                "Product Name": "product",
                "Version": "version",
                "Serial Number": "serial",
                "UUID": "uuid",
                "Family": "family",
            },
        ),
    )


def _make_inventory_chassis(lines: List[List[str]]) -> Attributes:
    return Attributes(
        path=["hardware", "chassis"],
        inventory_attributes=_make_dict(
            lines,
            {
                "Manufacturer": "manufacturer",
                "Type": "type",
            },
        ),
    )


# Note: This node is also being filled by lnx_cpuinfo
def _make_inventory_processor(lines: List[List[str]]) -> Generator[Attributes, None, None]:
    vendor_map = {
        "GenuineIntel": "intel",
        "Intel(R) Corporation": "intel",
        "AuthenticAMD": "amd",
    }
    cpu_info = _make_dict(
        lines,
        {
            "Manufacturer": ("vendor", lambda v: vendor_map.get(v, v)),
            "Max Speed": ("max_speed", _parse_speed),
            "Voltage": ("voltage", _parse_voltage),
            "Status": "status",
        },
    )

    if cpu_info.pop("Status", "") == "Unpopulated":
        # Only update our CPU information if the socket is populated
        return

    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes=cpu_info,
    )


def _make_inventory_physical_mem_array(lines: List[List[str]], array_number: int) -> Attributes:
    # We expect several possible arrays
    return Attributes(
        path=["hardware", "memory", "arrays", str(array_number)],
        inventory_attributes=_make_dict(
            lines,
            {
                "Location": "location",
                "Use": "use",
                "Error Correction Type": "error_correction",
                "Maximum Capacity": ("maximum_capacity", _parse_size),
            },
        ),
    )


def _make_inventory_mem_device(
    lines: List[List[str]],
    array_number: int,
) -> Generator[TableRow, None, None]:
    device = _make_dict(
        lines,
        {
            "Total Width": "total_width",  # 64 bits
            "Data Width": "data_width",  # 64 bits
            "Form Factor": "form_factor",  # SODIMM
            "Set": "set",  # None
            "Locator": "locator",  # PROC 1 DIMM 2
            "Bank Locator": "bank_locator",  # Bank 2/3
            "Type": "type",  # DDR2
            "Type Detail": "type_detail",  # Synchronous
            "Manufacturer": "manufacturer",  # Not Specified
            "Serial Number": "serial",  # Not Specified
            "Asset Tag": "asset_tag",  # Not Specified
            "Part Number": "part_number",  # Not Specified
            "Speed": "speed",  # 667 MHz
            "Size": "size",  # 2048 MB
        },
    )
    if device["size"] == "No Module Installed":
        return
    # Convert speed and size into numbers
    device["speed"] = _parse_speed(device.get("speed", "Unknown"))  # type: ignore[arg-type]
    device["size"] = _parse_size(device.get("size", "Unknown"))  # type: ignore[arg-type]

    key_keys = ["set"]  # match hp_proliant_mem!
    yield TableRow(
        path=["hardware", "memory", "arrays", str(array_number), "devices"],
        key_columns={k: device.pop(k) for k in key_keys},
        inventory_columns=device,
    )


def _make_dict(
    lines: List[List[str]],
    converter_map: Mapping[str, Converter],
) -> Dict[str, Union[float, str, None]]:
    dict_: Dict[str, Union[float, str, None]] = {}
    for name, raw_value, *_rest in lines:
        if name not in converter_map or raw_value == "Not Specified":
            continue

        converter = converter_map[name]
        if isinstance(converter, str):
            dict_[converter] = raw_value
            continue

        label, transform = converter
        value = transform(raw_value)
        if value is not None:
            dict_[label] = value

    return dict_


register.inventory_plugin(
    name="dmidecode",
    inventory_function=inventory_dmidecode,
)

#                              _          _
#  _ __   __ _ _ __ ___  ___  | |__   ___| |_ __   ___ _ __ ___
# | '_ \ / _` | '__/ __|/ _ \ | '_ \ / _ \ | '_ \ / _ \ '__/ __|
# | |_) | (_| | |  \__ \  __/ | | | |  __/ | |_) |  __/ |  \__ \
# | .__/ \__,_|_|  |___/\___| |_| |_|\___|_| .__/ \___|_|  |___/
# |_|                                      |_|
#


def _parse_date(value: str) -> Optional[float]:
    try:
        return time.mktime(time.strptime(value, "%m/%d/%Y"))
    except ValueError:
        return None


def _parse_size(v: str) -> Optional[float]:  # into Bytes (int)
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


def _parse_speed(v: str) -> Optional[float]:  # into Hz (float)
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


def _parse_voltage(v: str) -> Optional[float]:
    if not v or v == "Unknown":
        return None

    parts = v.split()
    return float(parts[0])


def _parse_time(v: str) -> float:  # 155 ns
    parts = v.split()
    if parts[1] == "ns":
        return float(parts[0]) / 1000000000.0
    return float(parts[0])  # assume seconds
