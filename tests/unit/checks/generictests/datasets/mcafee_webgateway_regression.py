#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mcafee_webgateway'


info = [['10', '20']]


freeze_time = '2019-05-27T05:30:07'


mock_item_state = {
    '': {
        'check_mcafee_webgateway.infections': (1558935006., 2),
        'check_mcafee_webgateway.connections_blocked': (1558935006., 2),
    },
}


discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {}, [
            (0, 'Infections: 8.0/s', [
                ('infections_rate', 8.0, None, None, None, None),
            ]),
            (0, 'Connections blocked: 18.0/s', [
                ('connections_blocked_rate', 18.0, None, None, None, None),
            ]),
        ]),
        (None, {'infections': (5, 10), 'connections_blocked': (10, 15)}, [
            (1, 'Infections: 8.0/s (warn/crit at 5.0/s/10.0/s)', [
                ('infections_rate', 8.0, 5, 10, None, None),
            ]),
            (2, 'Connections blocked: 18.0/s (warn/crit at 10.0/s/15.0/s)', [
                ('connections_blocked_rate', 18.0, 10, 15, None, None),
            ]),
        ]),
    ],
}
