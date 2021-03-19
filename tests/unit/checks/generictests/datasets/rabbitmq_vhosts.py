#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable

from typing import Any, Dict, List, Tuple

checkname = 'rabbitmq_vhosts'

info = [
    [
        '{"description": "Default virtual host", "message_stats": {"publish": 2, "publish_details": {"rate": 0.0}}, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "/"}'
    ]
]

discovery: Dict[str, List[Tuple[str, Dict[Any, Any]]]] = {'': [('/', {})]}

checks: Dict[str, List[Tuple[str, Dict[Any, Any], List[Tuple[int, str, List[Tuple[str, float, Any, Any, Any, Any]]]]]]] = {
    '': [
        (
            '/', {}, [
                (0, 'Description: Default virtual host', []),
                (
                    0, 'Total number of messages: 0', [
                        ('messages', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Ready messages: 0', [
                        ('messages_ready', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Unacknowledged messages: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Published messages: 2', [
                        ('message_publish', 2, None, None, None, None)
                    ]
                ),
                (
                    0, 'Rate: 0.0 1/s', [
                        ('message_publish_rate', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
