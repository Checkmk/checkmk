# -*- encoding: utf-8
# yapf: disable


checkname = 'mssql_blocked_sessions'


info = [['ID-1', 'No blocking sessions']]


discovery = {'': [('ID-1', {})]}


checks = {'': [('ID-1', {'state': 2}, [(0, 'No blocking sessions', [])])]}