#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Mapping, Sequence

# pylint: disable=no-else-return
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

SectionScaleio = Mapping[str, Mapping[str, Sequence[str]]]


def parse_scaleio(string_table: StringTable, scaleio_section_name: str) -> SectionScaleio:
    parsed: dict = {}
    sys_id = ""
    for line in string_table:
        if line[0].startswith(scaleio_section_name):
            sys_id = line[1].replace(":", "")
            parsed[sys_id] = {}
        elif sys_id in parsed:
            parsed[sys_id][line[0]] = line[1:]
    return parsed


# This converts data into MB for our df.include
def convert_scaleio_space(unit: str, value: float) -> float | None:
    """Convert the space from the storage pool to MB

    >>> convert_scaleio_space("Bytes", 1048576)
    1.0
    >>> convert_scaleio_space("KB", 1024.0)
    1.0
    >>> convert_scaleio_space("MB", 1.0)
    1.0
    >>> convert_scaleio_space("GB", 1.0)
    1024.0
    >>> convert_scaleio_space("TB", 1.0)
    1048576.0
    >>> convert_scaleio_space("Not_known", 1.0)

    """

    if unit == "Bytes":
        return value / 1024.0**2
    elif unit == "KB":
        return value / 1024.0
    elif unit == "MB":
        return value
    elif unit == "GB":
        return value * 1024.0
    elif unit == "TB":
        return value * 1024.0**2
    return None


# Values can be in every unit. We need Bytes for
# diskstat.include
def convert_to_bytes(tp, unit):
    if unit == "Bytes":
        return tp
    elif unit == "KB":
        return tp * 1024
    elif unit == "MB":
        return tp * 1024 * 1024
    elif unit == "GB":
        return tp * 1024 * 1024 * 1024
    elif unit == "TB":
        return tp * 1024 * 1024 * 1024 * 1024
    return None


def get_disks(item, read_data, write_data):
    read_tp = convert_to_bytes(int(read_data[-3].strip("(")), read_data[-2].strip(")"))
    write_tp = convert_to_bytes(int(write_data[-3].strip("(")), write_data[-2].strip(")"))

    disks = {
        item: {
            "node": None,
            "read_ios": int(read_data[0]),
            "read_throughput": read_tp,
            "write_ios": int(write_data[0]),
            "write_throughput": write_tp,
        }
    }
    return disks


def get_scaleio_data(item, parsed):
    return parsed.get(item)
