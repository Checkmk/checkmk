#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS

checkname = 'emc_isilon_quota'

info = [
    ['/ifs/data/pacs', '0', '1', '219902325555200', '0', '0', '3844608548041']
]

discovery = {'': [('/ifs/data/pacs', {})]}

checks = {
    '': [
        (
            '/ifs/data/pacs', FILESYSTEM_DEFAULT_LEVELS, [
                (
                    0, 'Used: 1.75% - 3.50 TiB of 200 TiB', [
                        (
                            'fs_used', 3666504.428902626, 167772160.0,
                            188743680.0, 0, 209715200.0
                        ), ('fs_size', 209715200.0, None, None, 0, None),
                        (
                            'fs_used_percent', 1.7483255524171, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        )
    ]
}
