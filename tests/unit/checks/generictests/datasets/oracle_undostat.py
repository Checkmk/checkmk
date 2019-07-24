# yapf: disable


checkname = 'oracle_undostat'


info = [['TUX2', '160', '3', '1081', '300', '0'],
        ['TUX3', '150', '2', '1041', '200', '1']]


discovery = {'': [('TUX2', {}), ('TUX3', {})]}


checks = {'': [('TUX2',
                {'levels': (600, 300), 'nospaceerrcnt_state': 2},
                [(0,
                  '18 m Undoretention (warn/crit at 10 m/5 m), 160 active undoblocks, 3 max concurrent transactions, 5 m max querylen, 0 space errors',
                  [('activeblk', 160, None, None, None, None),
                   ('transconcurrent', 3, None, None, None, None),
                   ('tunedretention', 1081, 600, 300, None, None),
                   ('querylen', 300, None, None, None, None),
                   ('nonspaceerrcount', 0, None, None, None, None)])]),
               ('TUX3',
                {'levels': (600, 300), 'nospaceerrcnt_state': 2},
                [(2,
                  '17 m Undoretention (warn/crit at 10 m/5 m), 150 active undoblocks, 2 max concurrent transactions, 200 s max querylen, 1 space errors(!!)',
                  [('activeblk', 150, None, None, None, None),
                   ('transconcurrent', 2, None, None, None, None),
                   ('tunedretention', 1041, 600, 300, None, None),
                   ('querylen', 200, None, None, None, None),
                   ('nonspaceerrcount', 1, None, None, None, None)])])]}