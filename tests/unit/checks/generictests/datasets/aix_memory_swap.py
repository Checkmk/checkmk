#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'aix_memory'

info = [
    ['32702464', 'memory', 'pages'], ['31736528', 'lruable', 'pages'],
    ['858141', 'free', 'pages'], ['4', 'memory', 'pools'],
    ['6821312', 'pinned', 'pages'], ['80.0', 'maxpin', 'percentage'],
    ['3.0', 'minperm', 'percentage'], ['90.0', 'maxperm', 'percentage'],
    ['8.8', 'numperm', 'percentage'], ['2808524', 'file', 'pages'],
    ['0.0', 'compressed', 'percentage'], ['0', 'compressed', 'pages'],
    ['8.8', 'numclient', 'percentage'], ['90.0', 'maxclient', 'percentage'],
    ['2808524', 'client', 'pages'], ['0', 'remote', 'pageouts', 'scheduled'],
    ['354', 'pending', 'disk', 'I/Os', 'blocked', 'with', 'no', 'pbuf'],
    ['860832', 'paging', 'space', 'I/Os', 'blocked', 'with', 'no', 'psbuf'],
    ['2228', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
    ['508', 'client', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
    [
        '1372', 'external', 'pager', 'filesystem', 'I/Os', 'blocked', 'with',
        'no', 'fsbuf'
    ],
    [
        '88.8', 'percentage', 'of', 'memory', 'used', 'for', 'computational',
        'pages'
    ],
    [
        'allocated', '=', '8257536', 'blocks', 'used', '=', '1820821',
        'blocks', 'free', '=', '6436715', 'blocks'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'levels': (150.0, 200.0)
            }, [
                (
                    0,
                    'Total (RAM + Swap): 94.36% - 117.71 GB of 124.75 GB RAM',
                    [
                        ('swap_used', 7458082816, None, None, 0, 33822867456),
                        (
                            'mem_used', 118930632704, None, None, 0,
                            133949292544
                        ),
                        (
                            'mem_used_percent', 88.78780204451873, None, None,
                            0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 126388715520, 200923938816.0,
                            267898585088.0, 0, 167772160000
                        )
                    ]
                ), (0, 'RAM: 88.79% - 110.76 GB of 124.75 GB', []),
                (0, 'Swap: 22.05% - 6.95 GB of 31.50 GB', [])
            ]
        )
    ]
}
