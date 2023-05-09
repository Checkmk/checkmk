#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'sap_hana_ess'

info = [['[[H11 11]]'], ['started', '0'], ['active', 'yes']]

discovery = {'': [('H11 11', {})]}

checks = {
    '': [
        (
            'H11 11', {}, [
                (0, 'Active status: yes', []),
                (
                    2, 'Started threads: 0', [
                        ('threads', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
