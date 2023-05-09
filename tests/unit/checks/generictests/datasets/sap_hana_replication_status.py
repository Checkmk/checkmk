#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'sap_hana_replication_status'

info = [
    ['[[H62', '10]]'], ['systemReplicationStatus:', '10'],
    ['this', 'system', 'is', 'not', 'a', 'system', 'replication', 'site'],
    ['[[Y04', '0]]'], ['systemReplicationStatus:', '0'], ['mode:', 'primary'],
    ['[[AH', '1234]]'], ['systemReplicationStatus:', '12'],
    ['this', 'system', 'is', 'either', 'not', 'running', 'or', 'not', 'primary', 'system', 'replication', 'site'],
    ['Local', 'System', 'Replication', 'State'],
    ['~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'],
    ['mode:', 'SYNC'],
    ['site', 'id:', '2'],
    ['site', 'name:', 'foo'],
    ['active', 'primary', 'site:', '1'],
    ['primary', 'masters:', 'host1', 'host2', 'host3']
    ]

discovery = {'': [('Y04 0', {}), ('AH 1234', {})]}


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
        ),
        (
            'AH 1234', {}, [
                (
                    0,
                    'System replication: passive',
                    []
                )
            ]
        )
    ]
}
