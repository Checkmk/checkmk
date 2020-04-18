#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'sap_hana_replication_status'

info = [
    ['[[H62', '10]]'], ['systemReplicationStatus:', '10'],
    ['this', 'system', 'is', 'not', 'a', 'system', 'replication', 'site'],
    ['[[Y04', '0]]'], ['systemReplicationStatus:', '0'], ['mode:', 'primary']
]

discovery = {'': [('Y04 0', {})]}

checks = {
    '': [
        (
            'Y04 0', {}, [
                (
                    3,
                    'System replication: unknown status from replication script',
                    []
                )
            ]
        )
    ]
}
