#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.cpu import ProcessorType
from .utils.wmi import get_wmi_time, parse_wmi_table, required_tables_missing, WMIQueryTimeoutError


class Section(NamedTuple):
    load: float
    timestamp: float
    processor_type: ProcessorType
    n_cores: int


def parse_wmi_cpuload(string_table: StringTable) -> Optional[Section]:
    wmi_tables = parse_wmi_table(string_table)
    if required_tables_missing(
            wmi_tables,
        [
            "computer_system",
            "system_perf",
        ],
    ):
        return None

    try:
        load = wmi_tables["system_perf"].get(0, "ProcessorQueueLength")
        timestamp = get_wmi_time(wmi_tables["system_perf"], 0)
        computer_system = wmi_tables["computer_system"]
    except (KeyError, WMIQueryTimeoutError):
        return None
    assert load

    try:
        n_cores = computer_system.get(0, "NumberOfLogicalProcessors")
        processor_type = ProcessorType.logical
    except (KeyError, WMIQueryTimeoutError):
        try:
            n_cores = computer_system.get(0, "NumberOfProcessors")
            processor_type = ProcessorType.physical
        except (KeyError, WMIQueryTimeoutError):
            return None

    # NumberOfLogicalProcessors can be an empty string, not sure why
    if not n_cores:
        return None

    return Section(
        int(load),
        timestamp,
        processor_type,
        int(n_cores),
    )


register.agent_section(
    name="wmi_cpuload",
    parse_function=parse_wmi_cpuload,
)
