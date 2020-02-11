# -*- encoding: utf-8
# yapf: disable
checkname = 'mssql_blocked_sessions'

info = [
    ['ID-1', 'No blocking sessions'],
    [u'MSSQLSERVER_SA', u'No blocking sessions'],
    [u'MSSQLSERVER_LIVE', u'No blocking sessions']
]

discovery = {
    '': [('ID-1', {}), (u'MSSQLSERVER_LIVE', {}), (u'MSSQLSERVER_SA', {})]
}

checks = {
    '': [
        ('ID-1', {
            'state': 1
        }, [(0, 'No blocking sessions', [])]),
        ('ID-1', {
            'state': 2
        }, [(0, 'No blocking sessions', [])]),
        (u'MSSQLSERVER_LIVE', {
            'state': 2
        }, [(0, 'No blocking sessions', [])]),
        (u'MSSQLSERVER_SA', {
            'state': 2
        }, [(0, 'No blocking sessions', [])])
    ]
}
