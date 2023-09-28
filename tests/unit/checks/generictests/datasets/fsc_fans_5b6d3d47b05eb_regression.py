#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "fsc_fans"


info = [["NULL", "NULL"], ["FAN1 SYS", "4140"]]


discovery = {"": [("FAN1 SYS", {})]}


checks = {"": [("FAN1 SYS", {"lower": (2000, 1000)}, [(0, "Speed: 4140 RPM", [])])]}
