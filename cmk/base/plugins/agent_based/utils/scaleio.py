#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, MutableMapping, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

ScaleioSection = Mapping[str, Mapping[str, Sequence[str]]]


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
    if unit == "KB":
        return value / 1024.0
    if unit == "MB":
        return value
    if unit == "GB":
        return value * 1024.0
    if unit == "TB":
        return value * 1024.0**2
    return None


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
