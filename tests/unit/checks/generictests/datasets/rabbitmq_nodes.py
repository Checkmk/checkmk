#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'rabbitmq_nodes'

freeze_time = '2020-03-18 15:38:00'

info = [
    [
        '{"fd_total": 1048576, "sockets_total": 943629, "mem_limit": 6608874700, "mem_alarm": false, "disk_free_limit": 50000000, "disk_free_alarm": false, "proc_total": 1048576, "uptime": 24469577, "run_queue": 1, "name": "rabbit@my-rabbit", "type": "disc", "running": true, "mem_used": 113299456, "fd_used": 34, "sockets_used": 0, "proc_used": 431, "gc_num": 282855, "gc_bytes_reclaimed": 17144463144, "io_file_handle_open_attempt_count": 11}'
    ]
]

discovery = {
    '': [('rabbit@my-rabbit', {})],
    'filedesc': [('rabbit@my-rabbit', {})],
    'sockets': [('rabbit@my-rabbit', {})],
    'proc': [('rabbit@my-rabbit', {})],
    'mem': [('rabbit@my-rabbit', {})],
    'uptime': [('rabbit@my-rabbit', {})],
    'gc': [('rabbit@my-rabbit', {})]
}

checks = {
    '': [
        (
            'rabbit@my-rabbit', {
                'state': 2,
                'disk_free_alarm': 2,
                'mem_alarm': 2
            }, [(0, 'Type: Disc', []), (0, 'Is running: yes', [])]
        )
    ],
    'filedesc': [
        (
            'rabbit@my-rabbit', {}, [
                (
                    0, 'File descriptors used: 34 of 1048576, 0.003%', [
                        ('open_file_descriptors', 34, None, None, 0, 1048576)
                    ]
                ),
                (
                    0, 'File descriptor open attempts: 11', [
                        (
                            'file_descriptors_open_attempts', 11, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ],
    'sockets': [
        (
            'rabbit@my-rabbit', {}, [
                (
                    0, 'Sockets used: 0 of 943629, 0%', [
                        ('sockets', 0, None, None, 0, 943629)
                    ]
                )
            ]
        )
    ],
    'proc': [
        (
            'rabbit@my-rabbit', {}, [
                (
                    0, 'Erlang processes used: 431 of 1048576, 0.04%', [
                        ('processes', 431, None, None, 0, 1048576)
                    ]
                )
            ]
        )
    ],
    'mem': [
        (
            'rabbit@my-rabbit', {}, [
                (
                    0,
                    'Memory used: 1.71% - 108 MiB of 6.15 GiB High watermark',
                    [('mem_used', 113299456, None, None, 0, 6608874700)]
                )
            ]
        )
    ],
    'uptime': [
        (
            'rabbit@my-rabbit', {}, [
                (
                    0, 'Up since Wed Mar 18 09:50:10 2020, uptime: 6:47:49', [
                        ('uptime', 24469.577, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'gc': [
        (
            'rabbit@my-rabbit', {}, [
                (
                    0, 'GC runs: 282855', [
                        ('gc_runs', 282855, None, None, None, None)
                    ]
                ),
                (
                    0, 'Bytes reclaimed by GC: 16.0 GiB', [
                        ('gc_bytes', 17144463144, None, None, None, None)
                    ]
                ),
                (
                    0, 'Runtime run queue: 1', [
                        ('runtime_run_queue', 1, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
