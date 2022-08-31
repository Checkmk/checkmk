#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping, MutableMapping, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

ScaleioSection = Mapping[str, Mapping[str, Sequence[str]]]

KNOWN_CONVERSION_VALUES_INTO_MB = {
    "Bytes": 1.0 / 1024.0**2,
    "KB": 1.0 / 1024,
    "MB": 1.0,
    "GB": 1024.0,
    "TB": 1024**2,
}

KNOWN_CONVERSION_VALUES_INTO_BYTES = {
    "Bytes": 1.0,
    "KB": 1024.0,
    "MB": 1024.0**2,
    "GB": 1024.0**3,
    "TB": 1024.0**4,
}


def convert_scaleio_space_into_mb(unit: str, value: float) -> float:
    """Convert the space from the storage pool to MB

    >>> convert_scaleio_space_into_mb("Bytes", 1048576)
    1.0
    >>> convert_scaleio_space_into_mb("KB", 1024.0)
    1.0
    >>> convert_scaleio_space_into_mb("MB", 1.0)
    1.0
    >>> convert_scaleio_space_into_mb("GB", 1.0)
    1024.0
    >>> convert_scaleio_space_into_mb("TB", 1.0)
    1048576.0

    """

    return value * KNOWN_CONVERSION_VALUES_INTO_MB[unit]


def convert_throughput_into_bytes(unit: str, throughput: float) -> float:
    """Convert the throughput values from the storage pool to Bytes

    >>> convert_throughput_into_bytes("Bytes", 1.0)
    1.0
    >>> convert_throughput_into_bytes("KB", 1.0)
    1024.0
    >>> convert_throughput_into_bytes("MB", 1.0)
    1048576.0
    >>> convert_throughput_into_bytes("GB", 1.0)
    1073741824.0
    >>> convert_throughput_into_bytes("TB", 1.0)
    1099511627776.0

    """

    return throughput * KNOWN_CONVERSION_VALUES_INTO_BYTES[unit]


def parse_scaleio(string_table: StringTable, scaleio_section_name: str) -> ScaleioSection:

    section: MutableMapping[str, MutableMapping[str, Sequence[str]]] = {}
    sys_id = ""

    for line in string_table:
        if line[0].startswith(scaleio_section_name):
            sys_id = line[1].replace(":", "")
            section.setdefault(sys_id, {})

        elif sys_id in section:
            section[sys_id][line[0]] = line[1:]

    return section
