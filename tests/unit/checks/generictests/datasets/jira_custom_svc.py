# -*- encoding: utf-8
# yapf: disable
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
        u'{"Jira', u'custom', u'2":', u'{"count":', u'398},', u'"Charged',
        u'avg":', u'{"avg":', u'"0.96"},', u'"Charged', u'sum":', u'{"sum":',
        u'48.0}}'
    ]
]

discovery = {
    '': [
        (u'Charged Avg', {}), (u'Charged Sum', {}), (u'Custom Service', {}),
        (u'Jira Custom 2', {})
    ]
}

checks = {
    '': [
        (
            u'Charged Avg', {}, [
                (
                    0, 'Average value: 0.96', [
                        ('jira_avg', 0.96, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'Charged Sum', {}, [
                (
                    0, 'Result of summed up values: 48', [
                        ('jira_sum', 48.0, None, None, None, None)
                    ]
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
            u'Jira Custom 2', {}, [
                (
                    0, 'Total number of issues: 398', [
                        ('jira_count', 398, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
