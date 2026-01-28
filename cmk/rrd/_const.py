#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

RRD_DEFAULT_CONFIG: Final = [
    "RRA:AVERAGE:0.50:1:2880",
    "RRA:AVERAGE:0.50:5:2880",
    "RRA:AVERAGE:0.50:30:4320",
    "RRA:AVERAGE:0.50:360:5840",
    "RRA:MAX:0.50:1:2880",
    "RRA:MAX:0.50:5:2880",
    "RRA:MAX:0.50:30:4320",
    "RRA:MAX:0.50:360:5840",
    "RRA:MIN:0.50:1:2880",
    "RRA:MIN:0.50:5:2880",
    "RRA:MIN:0.50:30:4320",
    "RRA:MIN:0.50:360:5840",
]

RRD_HEARTBEAT: Final = 8460
