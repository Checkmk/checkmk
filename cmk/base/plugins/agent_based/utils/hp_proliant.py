#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

MAP_TYPES_MEMORY: Final = {
    "1": 'other',
    "2": 'board',
    "3": 'cpqSingleWidthModule',
    "4": 'cpqDoubleWidthModule',
    "5": 'simm',
    "6": 'pcmcia',
    "7": 'compaq-specific',
    "8": 'DIMM',
    "9": 'smallOutlineDimm',
    "10": 'RIMM',
    "11": 'SRIMM',
    "12": 'FB-DIMM',
    "13": 'DIMM DDR',
    "14": 'DIMM DDR2',
    "15": 'DIMM DDR3',
    "16": 'DIMM FBD2',
    "17": 'FB-DIMM DDR2',
    "18": 'FB-DIMM DDR3',
}
