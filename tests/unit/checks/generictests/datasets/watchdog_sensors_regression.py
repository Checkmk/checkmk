# -*- encoding: utf-8
# yapf: disable


checkname = 'watchdog_sensors'


info = [[[u'3.2.0', u'1']],
        [[u'1', u'First Floor Ambient', u'1', u'213', u'37', u'60', u'']]]


discovery = {'': [(u'1', {})],
             'dew': [(u'1', {})],
             'humidity': [(u'1', {})],
             'temp': [(u'1', {})]}


checks = {'': [(u'1',
                {},
                [(0, 'available', []), (0, u'Location: First Floor Ambient', [])])],
          'dew': [(u'1',
                   {},
                   [(0, u'6.0 \xb0C', [('temp', 6.0, None, None, None, None)])])],
          'humidity': [(u'1',
                        {'levels': (50, 55), 'levels_lower': (10, 15)},
                        [(0, '37.0%', [('humidity', 37, 50, 55, None, None)])])],
          'temp': [(u'1',
                    {},
                    [(0, u'21.3 \xb0C', [('temp', 21.3, None, None, None, None)])])]}