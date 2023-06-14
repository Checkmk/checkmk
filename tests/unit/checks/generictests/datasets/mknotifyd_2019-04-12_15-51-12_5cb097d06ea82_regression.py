#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "mknotifyd"


info = [["[EX]"], ["Binary file (standard input) matches"]]


discovery = {"": [("EX", {})], "connection": []}


checks = {
    "": [
        (
            "EX",
            {},
            [
                (
                    2,
                    "The state file seems to be empty or corrupted. It is very likely that the spooler is not working properly",
                    [],
                )
            ],
        )
    ]
}
