#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS

checkname = 'emc_isilon_ifs'

info = [['615553001652224', '599743491129344']]

discovery = {'': [('Cluster', None)]}

checks = {
    '': [
        (
            'Cluster', FILESYSTEM_DEFAULT_LEVELS, [
                (
                    0, 'Used: 2.57% - 14.4 TiB of 560 TiB', [
                        (
                            'fs_used', 15077125, 469629670.4, 528333379.2, 0,
                            587037088
                        ), ('fs_size', 587037088, None, None, None, None),
                        (
                            'fs_used_percent', 2.5683428369691015, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
