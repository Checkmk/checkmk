#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'nfsiostat'

info = [
    [
        'abcdef123-x01:/bud_win_redvol/root/Oracle/tnsnames', 'mounted', 'on',
        '/mnt/eu.abext.example.com/FOO/RedVol/Oracle/tnsnames:', 'op/s', 'rpc',
        'bklog', '1.24', '0.00', 'read:', 'ops/s', 'kB/s', 'kB/op', 'retrans',
        'avg', 'RTT', '(ms)', 'avg', 'exe', '(ms)', '0.000', '0.000', '19.605',
        '0', '(0.0%)', '0.690', '0.690', 'write:', 'ops/s', 'kB/s', 'kB/op',
        'retrans', 'avg', 'RTT', '(ms)', 'avg', 'exe', '(ms)', '0.000',
        '0.000', '0.000', '0', '(0.0%)', '0.000', '0.000',
    ]
]

discovery = {
    '': [
        ("'abcdef123-x01:/bud_win_redvol/root/Oracle/tnsnames',", {}),
    ]
}

checks = {
    '': [
        (
            "'abcdef123-x01:/bud_win_redvol/root/Oracle/tnsnames',", {}, [
                (
                    0, 'Operations: 1.24/s', [
                        ('op_s', 1.24, None, None, None, None)
                    ]
                ),
                (
                    0, 'RPC Backlog: 0.00', [
                        ('rpc_backlog', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read operations /s: 0.000/s', [
                        ('read_ops', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Reads size /s: 0.000B/s', [
                        ('read_b_s', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read bytes per operation: 19.605B/op', [
                        ('read_b_op', 19.605, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read Retransmission: 0.0%', [
                        ('read_retrans', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read average RTT: 0.690/s', [
                        ('read_avg_rtt_ms', 0.69, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read average EXE: 0.690/s', [
                        ('read_avg_exe_ms', 0.69, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write operations /s: 0.000/s', [
                        ('write_ops_s', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Writes size /s: 0.000kB/s', [
                        ('write_b_s', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write bytes per operation: 0.000B/op', [
                        ('write_b_op', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write Retransmission: 0.000%', [
                        ('write_retrans', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write Average RTT: 0.000/ms', [
                        ('write_avg_rtt_ms', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write Average EXE: 0.000/ms', [
                        ('write_avg_exe_ms', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
    ]
}
