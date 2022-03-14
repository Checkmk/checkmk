#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucs_c_rack_server_faultinst:sep(9)>>>
# faultInst<TAB>severity critical<TAB>cause powerproblem<TAB>code F0883<TAB>descr Power supply 4 is in a degraded state, or has bad input voltage<TAB>affectedDN sys/rack-unit-1/psu-4
# faultInst<TAB>severity major<TAB>cause psuRedundancyFail<TAB>code F0743<TAB>descr Power Supply redundancy is lost : Reseat or replace Power Supply <TAB>affectedDN sys/rack-unit-1/psu
# faultInst<TAB>severity major<TAB>cause equipmentDegraded<TAB>code F0969<TAB>descr Storage Raid Battery 11 Degraded: please check the battery or the storage controller<TAB>affectedDN sys/rack-unit-1/board/storage-SAS-SLOT-SAS/raid-battery-11
# faultInst<TAB>severity major<TAB>cause equipmentInoperable<TAB>code F0531<TAB>descr Storage Raid Battery 11 is inoperable: Check Controller battery<TAB>affectedDN sys/rack-unit-1/board/storage-SAS-SLOT-SAS/raid-battery-11

from typing import Dict, List

from .agent_based_api.v1 import register, type_defs


def parse_ucs_c_rack_server_faultinst(string_table: type_defs.StringTable) -> Dict[str, List[str]]:
    """
    >>> parse_ucs_c_rack_server_faultinst([['faultInst', 'severity critical', 'cause powerproblem', 'code F0883', 'descr Broken', 'affectedDN sys/rack-unit-1/psu-4']])
    {'Severity': ['critical'], 'Cause': ['powerproblem'], 'Code': ['F0883'], 'Description': ['Broken'], 'Affected DN': ['rack-unit-1/psu-4']}
    >>> parse_ucs_c_rack_server_faultinst([])
    {}
    """
    parsed: Dict[str, List[str]] = {}
    key_translation = {"descr": "Description", "affectedDN": "Affected DN"}

    for fault_inst_data in string_table:
        for data in fault_inst_data[1:]:
            key, value = data.split(" ", 1)
            key = key_translation.get(key, key.capitalize())
            parsed.setdefault(key, []).append(value)

        parsed["Affected DN"][-1] = parsed["Affected DN"][-1].replace("sys/", "")

    return parsed


register.agent_section(
    name="ucs_c_rack_server_faultinst",
    parse_function=parse_ucs_c_rack_server_faultinst,
)
