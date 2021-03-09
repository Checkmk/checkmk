# -*- encoding: utf-8
# yapf: disable


checkname = 'mssql_blocked_sessions'


info = [['No blocking sessions']]


discovery = {'': [('', {})]}


checks = {'': [('', {'state': 2}, [(0, 'No blocking sessions', [])])]}