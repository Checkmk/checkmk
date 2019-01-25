checkname = 'jolokia_generic'

info = [
    ['Instance1', 'Mitglieder_Anzahl', -23, 'number'],
    ['Instance2', 'Mitglieder Anzahl', -23, 'number'],
    [
        'JIRA,com.atlassian.jira:type=web.requests,invocation.count', 'jira.name',
        'invocation.count', 'number'
    ],
    [
        'JIRA,com.atlassian.jira:type=web.requests,invocation.count', 'jira.value', '2624460',
        'number'
    ],
]

discovery = {
    '': [
        ('Instance1 Mitglieder_Anzahl', {}),
        ('Instance2 Mitglieder Anzahl', {}),
        ('JIRA,com.atlassian.jira:type=web.requests,invocation.count jira.value', {}),
    ],
    'rate': [],
    'string': []
}

checks = {
    '': [
        ('Instance1 Mitglieder_Anzahl', {}, [(0, '-23.0', [('generic_number', -23.0, None, None,
                                                            None, None)])]),
        ('Instance2 Mitglieder Anzahl', {}, [(0, '-23.0', [('generic_number', -23.0, None, None,
                                                            None, None)])]),
        ('JIRA,com.atlassian.jira:type=web.requests,invocation.count jira.name', {},
         [(3, "Non-numeric MBean value", [])]),
        ('JIRA,com.atlassian.jira:type=web.requests,invocation.count jira.value', {},
         [(0, "2624460.0", [('generic_number', 2624460.0, None, None, None, None)])]),
    ]
}
