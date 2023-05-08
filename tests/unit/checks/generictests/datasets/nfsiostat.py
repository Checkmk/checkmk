#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'nfsiostat'

info = [
    [
        'abcdef312-t2:/ifs/ic/abcdef_ticks', 'mounted', 'on',
        '/mnt/dubmdh_ticks:', 'op/s', 'rpc', 'bklog', '1.66', '0.00', 'read:',
        'ops/s', 'kB/s', 'kB/op', 'retrans', 'avg', 'RTT', '(ms)', 'avg',
        'exe', '(ms)', '0.276', '35.397', '128.271', '0', '(0.0%)', '11.251',
        '11.361', 'write:', 'ops/s', 'kB/s', 'kB/op', 'retrans', 'avg', 'RTT',
        '(ms)', 'avg', 'exe', '(ms)', '0.000', '0.000', '0.000', '0', '(0.0%)',
        '0.000', '0.000',
    ]
]

discovery = {
    '': [
        ("'abcdef312-t2:/ifs/ic/abcdef_ticks',", {}),
    ]
}

checks = {
    '': [
        (
            "'abcdef312-t2:/ifs/ic/abcdef_ticks',", {}, [
                (
                    0, 'Operations: 1.66/s', [
                        ('op_s', 1.66, None, None, None, None)
                    ]
                ),
                (
                    0, 'RPC Backlog: 0.00', [
                        ('rpc_backlog', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read operations /s: 0.276/s', [
                        ('read_ops', 0.276, None, None, None, None)
                    ]
                ),
                (
                    0, 'Reads size /s: 35.397B/s', [
                        ('read_b_s', 35.397, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read bytes per operation: 128.271B/op', [
                        ('read_b_op', 128.271, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read Retransmission: 0.0%', [
                        ('read_retrans', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read average RTT: 11.251/s', [
                        ('read_avg_rtt_ms', 11.251, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read average EXE: 11.361/s', [
                        ('read_avg_exe_ms', 11.361, None, None, None, None)
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
