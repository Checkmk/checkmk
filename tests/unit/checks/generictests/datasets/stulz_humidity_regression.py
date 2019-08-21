# -*- encoding: utf-8
# yapf: disable


checkname = 'stulz_humidity'


info = [[u'MICOS11Q', u'12', u'229376', u'15221', u'15221', u'NO'],
        [u'MICOS11Q', u'12', u'229376', u'15221', u'15221']]


discovery = {'': [(u'MICOS11Q', 'stulz_humidity_default_levels'),
                  (u'MICOS11Q', 'stulz_humidity_default_levels')]}


checks = {'': [(u'MICOS11Q',
                (35, 40, 60, 65),
                [(2,
                  '1.2% (warn/crit below 40.0%/35.0%)',
                  [('humidity', 1.2, 60, 65, 0, 100)])]),
               (u'MICOS11Q',
                (35, 40, 60, 65),
                [(2,
                  '1.2% (warn/crit below 40.0%/35.0%)',
                  [('humidity', 1.2, 60, 65, 0, 100)])])]}
