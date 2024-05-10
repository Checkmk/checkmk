#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_dynamodb_limits"

info = [
    [
        '[["number_of_tables",',
        '"Number',
        "of",
        'tables",',
        "256,",
        "3,",
        '"eu-central-1"],',
        '["read_capacity",',
        '"Read',
        'Capacity",',
        "80000,",
        "3,",
        '"eu-central-1"],',
        '["write_capacity",',
        '"Write',
        'Capacity",',
        "80000,",
        "3,",
        '"eu-central-1"]]',
    ],
    [
        '[["number_of_tables",',
        '"Number',
        "of",
        'tables",',
        "256,",
        "1,",
        '"us-east-1"],',
        '["read_capacity",',
        '"Read',
        'Capacity",',
        "80000,",
        "4,",
        '"us-east-1"],',
        '["write_capacity",',
        '"Write',
        'Capacity",',
        "80000,",
        "2,",
        '"us-east-1"]]',
    ],
]

discovery = {"": [("eu-central-1", {}), ("us-east-1", {})]}

checks = {
    "": [
        (
            "eu-central-1",
            {
                "number_of_tables": (None, 80.0, 90.0),
                "read_capacity": (None, 80.0, 90.0),
                "write_capacity": (None, 80.0, 90.0),
            },
            [
                (
                    0,
                    "No levels reached",
                    [
                        ("aws_dynamodb_number_of_tables", 3),
                        ("aws_dynamodb_read_capacity", 3),
                        ("aws_dynamodb_write_capacity", 3),
                    ],
                ),
                (0, "\nNumber of tables: 3 (of max. 256)"),
                (0, "\nRead Capacity: 3 (of max. 80000)"),
                (0, "\nWrite Capacity: 3 (of max. 80000)"),
            ],
        ),
        (
            "us-east-1",
            {
                "number_of_tables": (None, 80.0, 90.0),
                "read_capacity": (None, 80.0, 90.0),
                "write_capacity": (None, 80.0, 90.0),
            },
            [
                (
                    0,
                    "No levels reached",
                    [
                        ("aws_dynamodb_number_of_tables", 1),
                        ("aws_dynamodb_read_capacity", 4),
                        ("aws_dynamodb_write_capacity", 2),
                    ],
                ),
                (0, "\nNumber of tables: 1 (of max. 256)"),
                (0, "\nRead Capacity: 4 (of max. 80000)"),
                (0, "\nWrite Capacity: 2 (of max. 80000)"),
            ],
        ),
    ]
}
