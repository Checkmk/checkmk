#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'graylog_jvm'

info = [
    [
        u'{"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 461934992, "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840, "jvm.memory.heap.usage": 0.45284732435050595}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'Used heap space: 441 MiB', [
                        ('mem_heap', 461934992, None, None, None, None)
                    ]
                ),
                (
                    0, 'Committed heap space: 973 MiB', [
                        (
                            'mem_heap_committed', 1020067840, None, None, None,
                            None
                        )
                    ]
                )
            ]
        )
    ]
}
