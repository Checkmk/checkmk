#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable

from typing import Any, Dict, List, Tuple

checkname = 'rabbitmq_queues'

info = [
    [
        '{"memory": 16780, "message_stats": {"publish": 5, "publish_details": {"rate": 0.0}}, "messages": 5, "messages_ready": 5, "messages_unacknowledged": 0, "name": "hello", "node": "rabbit@my-rabbit", "state": "running", "type": "classic"}'
    ],
    [
        '{"memory": 9816, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue2", "node": "rabbit@my-rabbit", "state": "running", "type": "classic"}'
    ],
    [
        '{"memory": 68036, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue3", "node": "rabbit@my-rabbit", "state": "running", "type": "quorum"}'
    ]
]

discovery: Dict[str, List[Tuple[str, Dict[Any, Any]]]] = {'': [('hello', {}), ('my_queue2', {}), ('my_queue3', {})]}

checks: Dict[str, List[Tuple[str, Dict[Any, Any], List[Tuple[int, str, List[Tuple[str, float, Any, Any, Any, Any]]]]]]] = {
    '': [
        (
            'hello', {}, [
                (0, 'Type: Classic', []), (0, 'Is running: running', []),
                (0, 'Running on node: rabbit@my-rabbit', []),
                (
                    0, 'Total number of messages: 5', [
                        ('messages', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages ready: 5', [
                        ('messages_ready', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages unacknowledged: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages published: 5', [
                        ('messages_publish', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Rate: 0 1/s', [
                        ('messages_publish_rate', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Memory used: 16.4 KiB', [
                        ('mem_lnx_total_used', 16780, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'my_queue2', {}, [
                (0, 'Type: Classic', []), (0, 'Is running: running', []),
                (0, 'Running on node: rabbit@my-rabbit', []),
                (
                    0, 'Total number of messages: 0', [
                        ('messages', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages ready: 0', [
                        ('messages_ready', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages unacknowledged: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Memory used: 9.59 KiB', [
                        ('mem_lnx_total_used', 9816, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'my_queue3', {}, [
                (0, 'Type: Quorum', []), (0, 'Is running: running', []),
                (0, 'Running on node: rabbit@my-rabbit', []),
                (
                    0, 'Total number of messages: 0', [
                        ('messages', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages ready: 0', [
                        ('messages_ready', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages unacknowledged: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Memory used: 66.4 KiB', [
                        ('mem_lnx_total_used', 68036, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
