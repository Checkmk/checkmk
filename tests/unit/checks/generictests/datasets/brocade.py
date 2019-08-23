# yapf: disable
checkname = 'brocade'

info = [['1', '24', 'SLOT #0: TEMP #1'], ['2', '12', 'SLOT #0: TEMP #2'],
        ['3', '12', 'SLOT #0: TEMP #3'], ['4', '4687', 'FAN #1'], ['5', '4560', 'FAN #2'],
        ['6', '4821', 'FAN #3'], ['7', '1', 'Power Supply #1'], ['8', '1', 'Power Supply #2']]

discovery = {
    'fan': [('1', 'brocade_fan_default_levels'), ('2', 'brocade_fan_default_levels')],
    'power': [('1', None), ('2', None)],
    'temp': [('1', 'brocade_temp_default_levels'), ('2', 'brocade_temp_default_levels'),
             ('3', 'brocade_temp_default_levels')]
}

checks = {
    'fan': [('1', {
        'lower': (3000, 2800)
    }, [(0, 'Speed: 4687 RPM', [])]),
            ('2', {
                'lower': (3000, 2800)
            }, [(0, 'Speed: 4560 RPM', [])])],
    'power': [('1', {}, [(0, 'No problems found', [])]), ('2', {}, [(0, 'No problems found', [])])],
    'temp': [('1', {
        'levels': (55, 60)
    }, [(0, u'24 \xb0C', [('temp', 24, 55, 60, None, None)])]),
             ('2', {
                 'levels': (55, 60)
             }, [(0, u'12 \xb0C', [('temp', 12, 55, 60, None, None)])]),
             ('3', {
                 'levels': (55, 60)
             }, [(0, u'12 \xb0C', [('temp', 12, 55, 60, None, None)])])]
}
