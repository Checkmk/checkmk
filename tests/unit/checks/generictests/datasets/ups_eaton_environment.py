# -*- encoding: utf-8
# yapf: disable


checkname = 'ups_eaton_enviroment'


info = [
    ['1', '40', '3'],
]


discovery = {
    '': [
        (None, {}),
    ],
}


checks = {
    '': [
        (None, {'humidity': (65, 80), 'remote_temp': (40, 50), 'temp': (40, 50)}, [
            (1, u'Temperature: 1°C (warn/crit at 40°C/50°C),'
                u' Remote-Temperature: 40°C (warn/crit at 40°C/50°C)(!),'
                u' Humidity: 3% (warn/crit at 65%/80%)', [
                    ('temp', 1, 40, 50, None, None),
                    ('remote_temp', 40, 40, 50, None, None),
                    ('humidity', 3, 65, 80, None, None),
                ]),
        ]),
    ],
}
