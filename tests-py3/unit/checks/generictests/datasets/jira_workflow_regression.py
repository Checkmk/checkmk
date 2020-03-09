#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jira_workflow'

info = [
    [
        u'{"support', u'and":', u'{"error":', u'"Jira', u'error', u'400:',
        u'The', u'value', u"'support", u"and'", u'does', u'not', u'exist',
        u'for', u'the', u'field', u'\'project\'."}}'
    ], [u'{"checkmk":', u'{"in', u'review":', u'16}}']
]

discovery = {'': [(u'Checkmk/In Review', {}), (u'Support And/Error', {})]}

checks = {
    '': [
        (
            u'Checkmk/In Review', {}, [
                (
                    0, 'Total number of issues: 16', [
                        ('jira_count', 16, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'Support And/Error', {}, [
                (
                    2,
                    u"Jira error while searching (see long output for details)\nJira error 400: The value 'support and' does not exist for the field 'project'.",
                    []
                )
            ]
        )
    ]
}
