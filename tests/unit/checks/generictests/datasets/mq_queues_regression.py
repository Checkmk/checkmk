#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "mq_queues"


info = [["[[Queue_App1_App2]]"], ["1", "2", "3", "4"]]


discovery = {"": [("Queue_App1_App2", {})]}


checks = {
    "": [
        (
            "Queue_App1_App2",
            {"consumer_count_levels_upper": (None, None), "consumer_count_levels_lower": (None, None), "size": (None, None)},
            [
                (
                    0,
                    "Queue size: 1",
                    [
                        ("queue", 1, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "Enqueue count: 3",
                    [
                        ("enque", 3, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "Dequeue count: 4",
                    [
                        ("deque", 4, None, None, None, None),
                    ],
                )
            ],
        )
    ]
}
