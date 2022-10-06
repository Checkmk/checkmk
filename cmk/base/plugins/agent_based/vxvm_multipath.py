#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping
from typing import NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register


class VXVMMultipathDisk(NamedTuple):
    name: str
    status: str
    paths: float
    active_paths: float
    inactive_paths: float
    enclosure: str


VXVMMultipathSection = Mapping[str, VXVMMultipathDisk]


def parse_vxvm_multipath(string_table: StringTable) -> VXVMMultipathSection:
    vxvm_multipath_disks: MutableMapping[str, VXVMMultipathDisk] = {}

    for line in string_table:
        try:
            name, status, _enc_type, paths, active_paths, inactive_paths, enclosure = line
        except ValueError:
            continue

        vxvm_multipath_disks[name] = VXVMMultipathDisk(
            name=name,
            status=status,
            paths=float(paths),
            active_paths=float(active_paths),
            inactive_paths=float(inactive_paths),
            enclosure=enclosure,
        )

    return vxvm_multipath_disks


register.agent_section(
    name="vxvm_multipath",
    parse_function=parse_vxvm_multipath,
)
