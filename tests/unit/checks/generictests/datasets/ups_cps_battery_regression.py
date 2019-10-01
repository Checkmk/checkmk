# -*- encoding: utf-8
# yapf: disable


checkname = 'ups_cps_battery'


info = [[u'73', u'41', u'528000']]


discovery = {'': [(None, {})], 'temp': [('Battery', {})]}


checks = {'': [(None,
                {'capacity': (95, 90)},
                [(2, 'Capacity at 73% (warn/crit at 95/90%)', []),
                 (0, '88 minutes remaining on battery', [])])],
          'temp': [('Battery',
                    {},
                    [(0, u'41 \xb0C', [('temp', 41, None, None, None, None)])])]}
