checkname = 'lnx_thermal'

info = [['thermal_zone0', 'enabled', 'acpitz', '57000', '127000', 'critical'],
        ['thermal_zone1', 'enabled', 'acpitz', '65000', '100000', 'critical', '95500', 'passive'],
        ['thermal_zone2', 'pkg-temp-0', '44000', '0', 'passive', '0', 'passive'],
        [
            'thermal_zone3', '-', 'TSKN', '48000', '0', 'passive', '0', 'passive', '127000',
            'critical', '87000', 'hot', '77000', 'passive', '127000', 'active'
        ], ['thermal_zone4', '-', 'INT3400 Thermal', '20000'],
        [
            'thermal_zone5', '-', 'iwlwifi', '27000', '-32768000', 'passive', '-32768000',
            'passive', '-32768000', 'passive', '-32768000', 'passive', '-32768000', 'passive',
            '-32768000', 'passive', '-32768000', 'passive', '-32768000', 'passive'
        ]]

discovery = {
    '': [('Zone 0', {}), ('Zone 1', {}), ('Zone 2', {}), ('Zone 3', {}), ('Zone 4', {}),
         ('Zone 5', {})]
}

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
         }, [(0, u'44.0 \xb0C', [('temp', 44.0, 70.0, 80.0, None, None)])]),
         ('Zone 3', {
             'device_levels_handling': 'devdefault',
             'levels': (70.0, 80.0)
         }, [(0, u'48.0 \xb0C', [('temp', 48.0, 77.0, 87.0, None, None)])]),
         ('Zone 4', {
             'device_levels_handling': 'devdefault',
             'levels': (70.0, 80.0)
         }, [(0, u'20.0 \xb0C', [('temp', 20.0, 70.0, 80.0, None, None)])]),
         ('Zone 5', {
             'device_levels_handling': 'devdefault',
             'levels': (70.0, 80.0)
         }, [(0, u'27.0 \xb0C', [('temp', 27.0, 70.0, 80.0, None, None)])])]
}
