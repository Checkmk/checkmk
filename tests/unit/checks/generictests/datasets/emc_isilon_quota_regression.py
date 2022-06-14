#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'emc_isilon_quota'

info = [
    ['/ifs/data/pacs', '0', '1', '219902325555200', '0', '0', '3844608548041']
]

discovery = {'': [('/ifs/data/pacs', {})]}

checks = {
    '': [
        (
            '/ifs/data/pacs', {}, [
                (
                    0, '1.75% used (3.50 of 200 TiB)', [
                        (
                            'fs_used', 3666504.428902626, 167772160.0,
                            209715200.0, 0, 209715200.0
                        ), ('fs_size', 209715200.0, None, None, None, None),
                        (
                            'fs_used_percent', 1.7483255524171, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
