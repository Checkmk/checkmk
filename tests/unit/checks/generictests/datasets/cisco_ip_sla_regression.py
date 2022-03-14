#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'cisco_ip_sla'

info = [
    [
        [u'6', [10, 96, 66, 4], [10, 96, 27, 69], u'1'],
    ],
    [
        [u'6', u'', u'', u'9', u'5000'],
    ],
    [
        [u'6', u'6', u'', u'2', u'2', u'2'],
    ],
    [
        [u'6', u'25', u'1'],
    ],
]

discovery = {'': [('6', {})]}

checks = {
    '': [('6', {
             'completion_time_over_treshold_occured': 'no',
             'connection_lost_occured': 'no',
             'latest_rtt_completion_time': (250, 500),
             'latest_rtt_state': 'ok',
             'state': 'active',
             'timeout_occured': 'no'
         }, [(0, 'Target address: 10.96.66.4', []), (0, 'Source address: 10.96.27.69', []),
             (0, 'RTT type: jitter', []), (0, 'Threshold: 5000 ms', []), (0, 'State: active', []),
             (0, 'Connection lost occured: no', []), (0, 'Timeout occured: no', []),
             (0, 'Completion time over treshold occured: no', []),
             (0, 'Latest RTT completion time: 25 ms', [('rtt', 0.025, 0.25, 0.5, None, None)]),
             (0, 'Latest RTT state: ok', [])])]
}
