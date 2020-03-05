#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'emc_isilon_ifs'

info = [[u'615553001652224', u'599743491129344']]

discovery = {'': [('Cluster', None)]}

checks = {
    '': [
        (
            'Cluster', {}, [
                (
                    0, '2.57% used (14.38 of 559.84 TB)', [
                        (
                            'ifs', 15077125, 469629670.4, 528333379.2, 0,
                            587037088
                        ), ('fs_size', 587037088, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
