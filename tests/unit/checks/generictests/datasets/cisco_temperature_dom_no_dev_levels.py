# -*- encoding: utf-8
# yapf: disable

checkname = u'cisco_temperature'

parsed = {
    '14': {
        u'NoLevels': {
            'descr': '',
            'reading': 3.14,
            'raw_dev_state': u'1',
            'dev_state': (0, 'awesome'),
            'dev_levels': None
        }
    }
}

discovery = {'': [], 'dom': [(u'NoLevels', {})]}

checks = {
    '': [],
    'dom': [
        (
            u'NoLevels', {}, [
                (0, 'Status: awesome', []),
                (
                    0, 'Signal power: 3.14 dBm', [
                        ('signal_power_dbm', 3.14, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
