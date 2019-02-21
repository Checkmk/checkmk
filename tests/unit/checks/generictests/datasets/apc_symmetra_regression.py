checkname = 'apc_symmetra'

info = [[
    u'2', u'2', u'100', u'2', u'0', u'366000', u'2', u'06/20/2012', u'18', u'0',
    u'0001010000000000001000000000000000000000000000000000000000000000'
]]

discovery = {'': [(None, {})], 'elphase': [('Battery', {})], 'temp': [('Battery', {})]}

checks = {
    '': [(None, {
        'capacity': (95, 80),
        'calibration_state': 0,
        'battery_replace_state': 1
    }, [(0, 'Battery status: normal', []), (1, 'battery needs replacing', []),
        (0, 'Output status: on line (calibration invalid)', []),
        (0, 'Capacity: 100%', [('capacity', 100, 95, 80, 0, 100)]),
        (0, 'Time remaining: 61 m', [('runtime', 61.0, None, None, None, None)])]),
         (None, {
             'capacity': (95, 80),
             'calibration_state': 0,
             'battery_replace_state': 2
         }, [(0, 'Battery status: normal', []), (2, 'battery needs replacing', []),
             (0, 'Output status: on line (calibration invalid)', []),
             (0, 'Capacity: 100%', [('capacity', 100, 95, 80, 0, 100)]),
             (0, 'Time remaining: 61 m', [('runtime', 61.0, None, None, None, None)])])],
    'elphase': [('Battery', {
        'current': (1, 1)
    }, [(0, 'Current: 0.0 A', [('current', 0.0, 1, 1, None, None)])])],
    'temp': [('Battery', {
        'levels': (50, 60)
    }, [(0, u'18.0 \xb0C', [('temp', 18.0, 50, 60, None, None)])])]
}
