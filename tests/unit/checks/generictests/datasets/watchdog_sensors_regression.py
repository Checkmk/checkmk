# -*- encoding: utf-8
# yapf: disable


checkname = 'watchdog_sensors'


info = [[[u'3.2.0', u'1']],
        [[u'1', u'First Floor Ambient', u'1', u'213', u'37', u'60', u''],
         [u'2', u'Second Floor Ambient', u'1', u'200', u'30', u'40', u'']]]


discovery = {'': [(u'Watchdog 1', {}), (u'Watchdog 2', {})],
             'dew': [(u'Dew point 1', {}), (u'Dew point 2', {})],
             'humidity': [(u'Humidity 1', {}), (u'Humidity 2', {})],
             'temp': [(u'Temperature 1', {}), (u'Temperature 2', {})]}


checks = {'': [(u'Watchdog 1',
                {},
                [(0, 'available', []), (0, u'Location: First Floor Ambient', [])]),
               (u'Watchdog 2',
                {},
                [(0, 'available', []), (0, u'Location: Second Floor Ambient', [])])],
          'dew': [(u'Dew point 1',
                   {},
                   [(0, u'6.0 \xb0C', [('temp', 6.0, None, None, None, None)])]),
                  (u'Dew point 2',
                   {},
                   [(0, u'4.0 \xb0C', [('temp', 4.0, None, None, None, None)])])],
          'humidity': [(u'Humidity 1',
                        {'levels': (50, 55), 'levels_lower': (10, 15)},
                        [(0, '37.0%', [('humidity', 37, 50, 55, None, None)])]),
                       (u'Humidity 2',
                        {'levels': (50, 55), 'levels_lower': (10, 15)},
                        [(0, '30.0%', [('humidity', 30, 50, 55, None, None)])])],
          'temp': [(u'Temperature 1',
                    {},
                    [(0, u'21.3 \xb0C', [('temp', 21.3, None, None, None, None)])]),
                   (u'Temperature 2',
                    {},
                    [(0, u'20.0 \xb0C', [('temp', 20.0, None, None, None, None)])])]}
