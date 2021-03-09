# -*- encoding: utf-8
# yapf: disable


checkname = u'cisco_temperature'


parsed = {
    '14': {
        u'NoLevels': {
            'raw_dev_state': u'1',
            'dev_levels': None,
            'reading': 3.14,
            'dev_state': (0, 'awesome'),
            'descr': '',
        },
    },
}


checks = {
    '': [],
    'dom': [
        ('NoLevels', {}, [
            (0, 'Status: awesome', []),
            (0, 'Signal power: 3.14 dBm', [('signal_power_dbm', 3.14)]),
        ]),
    ],
}
