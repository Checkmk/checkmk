#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "netapp_api_connection"

info = [
    ["line_0_element_0", "line_0_element_1"],
    ["line_1_element_0", "line_1_element_1"],
    ["line_2_element_0", "line_2_element_1", "line_2_element_2"],
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"warning_overrides": []},
            [
                (
                    1,
                    "line_0_element_0 line_0_element_1, line_1_element_0 line_1_element_1, line_2_element_0 line_2_element_1 line_2_element_2",
                    [],
                )
            ],
        )
    ]
}
