#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "liebert_compressor"


info = [
    [
        "Compressor Head Pressure",
        "5.9",
        "bar",
        "Compressor Head Pressure",
        "6.1",
        "bar",
        "Compressor Head Pressure",
        "Unavailable",
        "bar",
        "Compressor Head Pressure",
        "0.0",
        "bar",
    ]
]


discovery = {
    "": [
        ("Compressor Head Pressure 2", {}),
        ("Compressor Head Pressure 4", {}),
        ("Compressor Head Pressure", {}),
    ]
}


checks = {
    "": [
        ("Compressor Head Pressure 2", {"levels": (8, 12)}, [(0, "Head pressure: 6.10 bar", [])]),
        ("Compressor Head Pressure 4", {"levels": (8, 12)}, [(0, "Head pressure: 0.00 bar", [])]),
        ("Compressor Head Pressure", {"levels": (8, 12)}, [(0, "Head pressure: 5.90 bar", [])]),
    ],
}
