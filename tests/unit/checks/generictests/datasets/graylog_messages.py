#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'graylog_messages'

info = [['{"events": 8569688}']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'Total number of messages: 8569688', [
                        ('messages', 8569688, None, None, None, None)
                    ]
                ),
                (
                    0, 'Average number of messages (30 minutes 0 seconds): 0.00', [
                        ('msgs_avg', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of messages last 30 minutes 0 seconds: 0.00', [
                        ('graylog_diff', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
