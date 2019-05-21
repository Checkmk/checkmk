# -*- encoding: utf-8
# yapf: disable


checkname = 'akcp_exp_humidity'


info = [[u'Dual Humidity Port 1', u'30', u'7', u'1']]


discovery = {'': [(u'Dual Humidity Port 1', 'akcp_humidity_defaultlevels')]}


checks = {'': [(u'Dual Humidity Port 1',
                (30, 35, 60, 65),
                [(2, 'State: sensor error', []),
                 (1,
                  '30.0% (warn/crit below 35.0%/30.0%)',
                  [('humidity', 30, 60, 65, 0, 100)])])]}