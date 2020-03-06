# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = 'splunk_alerts'


info = [[u'5']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Number of fired alerts: 5',
                  [('fired_alerts', 5, None, None, None, None)])])]}
