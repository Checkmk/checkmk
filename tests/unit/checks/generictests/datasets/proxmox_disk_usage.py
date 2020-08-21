#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = 'proxmox_disk_usage'

info = [['{"disk": 264447721472, "max_disk": 688328540160}']]

discovery = {'': [(None, {})]}

checks = {
    '': [(
        None,
        {
            'levels': (80.0, 90.0)
        },
        [(
            0,
            'Usage: 246.29 GB',
            [('fs_used', 264447721472, 55066283212800.0, 61949568614400.0, 0.0, 688328540160.0)],
        )],
    )]
}
