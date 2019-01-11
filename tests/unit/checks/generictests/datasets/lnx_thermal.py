checkname = 'lnx_thermal'

info = [['thermal_zone0', 'enabled', 'acpitz', '57000', '127000', 'critical'],
        ['thermal_zone1', 'enabled', 'acpitz', '65000', '100000', 'critical', '95500', 'passive'],
        ['thermal_zone2', 'pkg-temp-0', '44000', '0', 'passive', '0', 'passive']]

discovery = {'': [('Zone 0', {}), ('Zone 1', {}), ('Zone 2', {})]}

checks = {
    '': [('Zone 0', {
        'device_levels_handling': 'devdefault',
        'levels': (70.0, 80.0)
    }, [(0, u'57.0 \xb0C', [('temp', 57.0, 127.0, 127.0, None, None)])]),
         ('Zone 1', {
             'device_levels_handling': 'devdefault',
             'levels': (70.0, 80.0)
         }, [(0, u'65.0 \xb0C', [('temp', 65.0, 95.5, 100.0, None, None)])]),
         ('Zone 2', {
             'device_levels_handling': 'devdefault',
             'levels': (70.0, 80.0)
         }, [(0, u'44.0 \xb0C', [('temp', 44.0, 70.0, 80.0, None, None)])])]
}
