# yapf: disable


checkname = 'ups_eaton_enviroment'


info = [['1', '40', '3']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'humidity': (65, 80), 'remote_temp': (40, 50), 'temp': (40, 50)},
                [(1,
                  u'Temperature: 1\xb0C (warn/crit at 40\xb0C/50\xb0C), Remote-Temperature: 40\xb0C (warn/crit at 40\xb0C/50\xb0C)(!), Humidity: 3% (warn/crit at 65%/80%)',
                  [('temp', 1, 40, 50, None, None),
                   ('remote_temp', 40, 40, 50, None, None),
                   ('humidity', 3, 65, 80, None, None)])])]}