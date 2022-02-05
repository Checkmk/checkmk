#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from ..agent_based_api.v1 import startswith
from ..agent_based_api.v1.type_defs import StringTable
from .cpu import Load, Section

DETECT_PEAKFLOW_SP = startswith(".1.3.6.1.2.1.1.1.0", "Peakflow SP")
DETECT_PEAKFLOW_TMS = startswith(".1.3.6.1.2.1.1.1.0", "Peakflow")
DETECT_PRAVAIL = startswith(".1.3.6.1.2.1.1.1.0", "Pravail")


def parse_arbor_cpu_load(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_arbor_cpu_load([["112", "156", "345"]])
    Section(load=Load(load1=1.12, load5=1.56, load15=3.45), num_cpus=1, threads=None, type=<ProcessorType.unspecified: 0>)
    """
    return (
        Section(
            load=Load(*(float(l) / 100 for l in string_table[0])),
            num_cpus=1,
        )
        if string_table
        else None
    )
