#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'fjdarye200_pools'

info = [['0', '117190584', '105269493']]

discovery = {'': [('0', {})]}

checks = {
    '': [
        (
            '0', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    1,
                    '89.83% used (100 of 112 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 105269493, 93752467.2, 105471525.6, 0,
                            117190584
                        ), ('fs_size', 117190584, None, None, None, None),
                        (
                            'fs_used_percent', 89.82760338492724, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
