#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jira_workflow'

info = [
    [
        u'{"my_project1":', u'{"in', u'progress":', u'16,', u'"waiting":',
        u'56,', u'"need', u'help":', u'42}}'
    ]
]

discovery = {
    '': [
        (u'My_Project1/In Progress', {}), (u'My_Project1/Need Help', {}),
        (u'My_Project1/Waiting', {})
    ]
}

checks = {
    '': [
        (
            u'My_Project1/In Progress', {}, [
                (
                    0, 'Total number of issues: 16', [
                        ('jira_count', 16, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'My_Project1/Need Help', {}, [
                (
                    0, 'Total number of issues: 42', [
                        ('jira_count', 42, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'My_Project1/Waiting', {}, [
                (
                    0, 'Total number of issues: 56', [
                        ('jira_count', 56, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
