# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = 'mssql_blocked_sessions'


info = [
    ['ID 1', 'No blocking sessions'],
    ['ID 1', '1', '232292187', 'Foo', '2'],
]


discovery = {'': [('ID 1', {})]}


checks = {'': [(
    'ID 1',
    {'state': 2},
    [
        (2, 'Summary: 1 blocked by 1 ID(s)', []),
        (0, '\nSession 1 blocked by 2 (Type: Foo, Wait: 2.7 d)', [])
    ]
)]}
