#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "liebert_reheating"


info = [["Reheating is awesome!", "81.3", "%"], ["This value ignored", "21.1", "def C"]]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {"levels": (80, 90)},
            [
                (
                    1,
                    "81.30 % (warn/crit at 80.00 %/90.00 %)",
                    [
                        ("filehandler_perc", 81.3, 80, 90, None, None),
                    ],
                ),
            ],
        ),
    ],
}
