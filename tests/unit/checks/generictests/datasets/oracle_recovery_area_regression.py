# -*- encoding: utf-8
# yapf: disable


checkname = 'oracle_recovery_area'


info = [[u'AIMDWHD1', u'300', u'51235', u'49000', u'300']]


discovery = {'': [(u'AIMDWHD1', {})]}


checks = {'': [(u'AIMDWHD1',
                {'levels': (70.0, 90.0)},
                [(2,
                  '47.85 GB out of 50.03 GB used (95.1%, warn/crit at 70.0%/90.0%), 300.00 MB reclaimable',
                  [('used', 49000, 35864.5, 46111.5, 0, 51235),
                   ('reclaimable', 300, None, None, None, None)])]),
               ]}
