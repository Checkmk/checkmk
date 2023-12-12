#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "f5_bigip_cpu_temp"

info = [["1", "40"]]

discovery = {"": [("1", {})]}

checks = {"": [("1", {"levels": (60, 80)}, [(0, "40 °C", [("temp", 40, 60.0, 80.0, None, None)])])]}
