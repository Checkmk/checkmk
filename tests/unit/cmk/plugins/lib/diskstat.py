#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

LEVELS = {
    "horizon": 90,
    "levels_lower": ("absolute", (2.0, 4.0)),
    "levels_upper": ("absolute", (10.0, 20.0)),
    "levels_upper_min": (10.0, 15.0),
    "period": "wday",
}
