#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'netapp_api_snapvault'

info = [[
    'snapvault /vol/ipb_datap/', 'status idle state snapvaulted', 'lag-time 53812',
    'source-system 172.31.12.15'
],
        [
            'snapvault /vol/ipb_datas/', 'status idle state snapvaulted', 'lag-time 53812',
            'source-system 172.31.12.15'
        ],
        [
            'snapvault /vol/ipb_user/', 'status idle state snapvaulted', 'lag-time 97007',
            'source-system 172.31.12.15'
        ],
        [
            'snapvault /vol/ipb_vol0/', 'status idle state snapvaulted', 'lag-time 97011',
            'source-system 172.31.12.15'
        ]]

discovery = {
    '': [('/vol/ipb_datap/', {}), ('/vol/ipb_datas/', {}), ('/vol/ipb_user/', {}),
         ('/vol/ipb_vol0/', {})]
}

checks = {
    '': [('/vol/ipb_datap/', {}, [(0, 'Source-System: 172.31.12.15', []),
                                  (0, 'Status: idle state snapvaulted', []),
                                  (0, 'Lag-Time: 14 h', [PerfValue('lag_time_minutes', 896, None, None, None, None)]])]),
         ('/vol/ipb_datas/', {}, [(0, 'Source-System: 172.31.12.15', []),
                                  (0, 'Status: idle state snapvaulted', []),
                                  (0, 'Lag-Time: 14 h', [PerfValue('lag_time_minutes', 896, None, None, None, None)]])]),
         ('/vol/ipb_user/', {}, [(0, 'Source-System: 172.31.12.15', []),
                                 (0, 'Status: idle state snapvaulted', []), (0, 'Lag-Time: 26 h',
                                                                             [PerfValue('lag_time_minutes', 1616, None, None, None, None)]])]),
         ('/vol/ipb_vol0/', {}, [(0, 'Source-System: 172.31.12.15', []),
                                 (0, 'Status: idle state snapvaulted', []), (0, 'Lag-Time: 26 h',
                                                                             [PerfValue('lag_time_minutes', 1616, None, None, None, None)]])])]
}
