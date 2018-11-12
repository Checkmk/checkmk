checkname = 'jolokia_generic'

info = [
    ['Instance1', 'Mitglieder_Anzahl', -23, 'number'],
    ['Instance2', 'Mitglieder Anzahl', -23, 'number'],
]

discovery = {
    '': [
        ('Instance1 MBean Mitglieder_Anzahl', {}),
        ('Instance2 MBean Mitglieder Anzahl', {}),
    ],
    'rate': [],
    'string': []
}

checks = {
    '': [
        ('Instance1 MBean Mitglieder_Anzahl', 'default',
         [(0, '-23.0', [('generic_number', -23.0, None, None, None, None)])]),
        ('Instance2 MBean Mitglieder Anzahl', 'default',
         [(0, '-23.0', [('generic_number', -23.0, None, None, None, None)])]),
    ]
}
