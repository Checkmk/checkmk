#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "pulse_secure_temp"

info = [["27"]]

discovery = {"": [("IVE", {})]}

checks = {
    "": [("IVE", {"levels": (70.0, 75.0)}, [(0, "27 °C", [("temp", 27, 70.0, 75.0, None, None)])])]
}
