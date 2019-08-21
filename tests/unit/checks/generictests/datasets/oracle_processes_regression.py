# -*- encoding: utf-8
# yapf: disable


checkname = 'oracle_processes'


info = [[u'FDMTST', u'50', u'300'],
        [u'METWFPRD', u'46', u'150'],
        [u'METRODEV', u'138', u'1000'],
        [u'TLDTST', u'122', u'500'],
        [u'FDMPRD', u'125', u'300'],
        [u'FARMPRD', u'54', u'300'],
        [u'DB1DEV2', u'1152', u'1500']]


discovery = {'': [(u'DB1DEV2', {}),
                  (u'FARMPRD', {}),
                  (u'FDMPRD', {}),
                  (u'FDMTST', {}),
                  (u'METRODEV', {}),
                  (u'METWFPRD', {}),
                  (u'TLDTST', {})]}


checks = {'': [(u'DB1DEV2',
                {'levels': (70.0, 90.0)},
                [(1,
                  '1152 of 1500 processes are used (76%, warn/crit at 70%/90%)',
                  [('processes', 1152, 1050.0, 1350.0, None, None)])]),
               (u'FARMPRD',
                {'levels': (70.0, 90.0)},
                [(0,
                  '54 of 300 processes are used (18%, warn/crit at 70%/90%)',
                  [('processes', 54, 210.0, 270.0, None, None)])]),
               (u'FDMPRD',
                {'levels': (70.0, 90.0)},
                [(0,
                  '125 of 300 processes are used (41%, warn/crit at 70%/90%)',
                  [('processes', 125, 210.0, 270.0, None, None)])]),
               (u'FDMTST',
                {'levels': (70.0, 90.0)},
                [(0,
                  '50 of 300 processes are used (16%, warn/crit at 70%/90%)',
                  [('processes', 50, 210.0, 270.0, None, None)])]),
               (u'METRODEV',
                {'levels': (70.0, 90.0)},
                [(0,
                  '138 of 1000 processes are used (13%, warn/crit at 70%/90%)',
                  [('processes', 138, 700.0, 900.0, None, None)])]),
               (u'METWFPRD',
                {'levels': (70.0, 90.0)},
                [(0,
                  '46 of 150 processes are used (30%, warn/crit at 70%/90%)',
                  [('processes', 46, 105.0, 135.0, None, None)])]),
               (u'TLDTST',
                {'levels': (70.0, 90.0)},
                [(0,
                  '122 of 500 processes are used (24%, warn/crit at 70%/90%)',
                  [('processes', 122, 350.0, 450.0, None, None)])])]}