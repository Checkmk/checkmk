#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = u'cisco_temperature'

parsed = {
    '14': {
        u'NoLevels': {
            'descr': '',
            'reading': 3.14,
            'raw_dev_state': u'1',
            'dev_state': (0, 'awesome'),
            'dev_levels': None
        }
    }
}

discovery = {'': [], 'dom': [(u'NoLevels', {})]}

checks = {
    '': [],
    'dom': [
        (
            u'NoLevels', {}, [
                (0, 'Status: awesome', []),
                (
                    0, 'Signal power: 3.14 dBm', [
                        ('signal_power_dbm', 3.14, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
