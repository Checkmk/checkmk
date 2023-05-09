#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jolokia_generic'

freeze_time = '2019-10-14 20:55:30'

info = [
    ['Instance1', 'Mitglieder_Anzahl', '-23', 'number'],
    ['Instance2', 'Mitglieder Anzahl', '-23', 'number'],
    ['Instance2', 'Beitritte', '42', 'rate'],
    ['Instance2', 'Current Motto', 'Never gonna give you up', 'string'],
    [
        'JIRA,com.atlassian.jira:type=web.requests,invocation.count',
        'jira.name', 'invocation.count', 'number'
    ],
    [
        'JIRA,com.atlassian.jira:type=web.requests,invocation.count',
        'jira.value', '2624460', 'number'
    ]
]

discovery = {
    '': [
        ('Instance1 Mitglieder_Anzahl', {}),
        ('Instance2 Mitglieder Anzahl', {}),
        (
            'JIRA,com.atlassian.jira:type=web.requests,invocation.count jira.value',
            {}
        )
    ],
    'rate': [('Instance2 Beitritte', {})],
    'string': [('Instance2 Current Motto', {})]
}

checks = {
    '': [
        (
            'Instance1 Mitglieder_Anzahl', {}, [
                (
                    0, '-23.00', [
                        ('generic_number', -23.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'Instance2 Mitglieder Anzahl', {}, [
                (
                    0, '-23.00', [
                        ('generic_number', -23.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'JIRA,com.atlassian.jira:type=web.requests,invocation.count jira.name',
            {}, []
        ),
        (
            'JIRA,com.atlassian.jira:type=web.requests,invocation.count jira.value',
            {}, [
                (
                    0, '2624460.00', [
                        ('generic_number', 2624460.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'rate': [
        (
            'Instance2 Beitritte', {}, [
                (
                    0, '0.33', [
                        (
                            'generic_rate', 0.328125, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ],
    'string':
    [('Instance2 Current Motto', {}, [(0, 'Never gonna give you up', [])])]
}


mock_item_state = {'rate': (1571086402, 0)}
