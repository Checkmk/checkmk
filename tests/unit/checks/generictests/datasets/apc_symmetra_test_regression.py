#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "apc_symmetra_test"


info = [["1", "03/09/2015"]]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {"levels_elapsed_time": None},
            [(0, "Result of self test: OK, Date of last test: 03/09/2015", [])],
        )
    ]
}
