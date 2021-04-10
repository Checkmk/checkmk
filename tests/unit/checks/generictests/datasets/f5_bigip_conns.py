#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_conns'

info = [['32', '1', '23933', '0', '2166']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'conns': (25000, 30000),
                'ssl_conns': (25000, 30000),
                'http_req_rate': (500, 1000)
            }, [
                (
                    0, 'Connections: 32.00', [
                        ('connections', 32, 25000.0, 30000.0, None, None)
                    ]
                ),
                (
                    0, 'SSL connections: 1.00', [
                        ('connections_ssl', 1, 25000.0, 30000.0, None, None)
                    ]
                ),
                (
                    0, 'Connections/s: 0.00', [
                        ('connections_rate', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'HTTP requests/s: 0.00',
                    [('requests_per_second', 0.0, 500.0, 1000.0, None, None)]
                )
            ]
        )
    ]
}
