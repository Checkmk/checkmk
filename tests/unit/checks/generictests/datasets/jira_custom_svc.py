#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jira_custom_svc'

info = [
    [
        u'{"Custom', u'Service":', u'{"error":', u'"Jira', u'error', u'400:',
        u'Error', u'in', u'the', u'JQL', u'Query:', u"'for'", u'is', u'a',
        u'reserved', u'JQL', u'word.', u'You', u'must', u'surround', u'it',
        u'in', u'quotation', u'marks', u'to', u'use', u'it', u'in', u'a',
        u'query.', u'(line', u'1,', u'character', u'40)"}}'
    ],
    [
        u'{"Custom', u'error":', u'{"error":', u'"Jira', u'error', u'400:',
        u'Error', u'in', u'the', u'JQL', u'Query:', u'Expecting', u'operator',
        u'but', u'got', u"'closed'.", u'The', u'valid', u'operators', u'are',
        u"'=',", u"'!=',", u"'<',", u"'>',", u"'<=',", u"'>=',", u"'~',",
        u"'!~',", u"'IN',", u"'NOT", u"IN',", u"'IS'", u'and', u"'IS",
        u"NOT'.", u'(line', u'1,', u'character', u'30)"}}'
    ],
    [
        u'{"Jira', u'custom', u'2":', u'{"count":', u'414},', u'"Custom',
        u'avg":', u'{"avg_sum":', u'37.0,', u'"avg_total":', u'50,', u'"avg":',
        u'"0.74"},', u'"Custom', u'sum":', u'{"sum":', u'37.0}}'
    ]
]

discovery = {
    '': [
        (u'Custom Avg', {}), (u'Custom Error', {}), (u'Custom Service', {}),
        (u'Custom Sum', {}), (u'Jira Custom 2', {})
    ]
}

checks = {
    '': [
        (
            u'Custom Avg', {}, [
                (
                    0, 'Average value: 0.74', [
                        ('jira_avg', 0.74, None, None, None, None)
                    ]
                ),
                (0, '(Summed up values: 37.0 / Total search results: 50)', [])
            ]
        ),
        (
            u'Custom Error', {}, [
                (
                    2,
                    u"Jira error while searching (see long output for details)\nJira error 400: Error in the JQL Query: Expecting operator but got 'closed'. The valid operators are '=', '!=', '<', '>', '<=', '>=', '~', '!~', 'IN', 'NOT IN', 'IS' and 'IS NOT'. (line 1, character 30)",
                    []
                )
            ]
        ),
        (
            u'Custom Service', {}, [
                (
                    2,
                    u"Jira error while searching (see long output for details)\nJira error 400: Error in the JQL Query: 'for' is a reserved JQL word. You must surround it in quotation marks to use it in a query. (line 1, character 40)",
                    []
                )
            ]
        ),
        (
            u'Custom Sum', {}, [
                (
                    0, 'Result of summed up values: 37', [
                        ('jira_sum', 37.0, None, None, None, None)
                    ]
                ),
                (
                    0, u'Difference last 7 days 0 hours: 0.00', [
                        ('jira_diff', 0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'Jira Custom 2', {}, [
                (
                    0, 'Total number of issues: 414', [
                        ('jira_count', 414, None, None, None, None)
                    ]
                ),
                (
                    0, u'Difference last 7 days 0 hours: 0.00', [
                        ('jira_diff', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
