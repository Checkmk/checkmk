# -*- encoding: utf-8
# yapf: disable


checkname = 'ups_socomec_in_voltage'


info = [[u'1', u'2300']]


discovery = {'': [(u'1', 'ups_in_voltage_default_levels')]}


checks = {'': [(u'1',
                (210, 180),
                [(0,
                  'in voltage: 230V, (warn/crit at 210V/180V)',
                  [('in_voltage', 230, 210, 180, 150, None)])])]}
