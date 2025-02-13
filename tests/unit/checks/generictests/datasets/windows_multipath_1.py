#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "windows_multipath"

info = [
    [
        "C:\\Program",
        "Files",
        "(x86)\\check_mk\\plugins\\windows_multipath.ps1(19,",
        "1)",
        "(null):",
        "0x80041010",
    ]
]

discovery = {"": []}
