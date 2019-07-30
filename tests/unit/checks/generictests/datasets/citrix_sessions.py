# yapf: disable


checkname = 'citrix_sessions'


info = [['sessions', '1'], ['active_sessions', '1'], ['inactive_sessions', '0']]


discovery = {'': [(None, 'citrix_sessions_default_levels')]}


checks = {'': [(None,
                {'active': (60, 65), 'inactive': (10, 15), 'total': (60, 65)},
                [(0, 'Total: 1', [('total', 1, 60, 65, None, None)]),
                 (0, 'Active: 1', [('active', 1, 60, 65, None, None)]),
                 (0, 'Inactive: 0', [('inactive', 0, 10, 15, None, None)])])]}