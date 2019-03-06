# yapf: disable

checkname = 'cpu'

info = [[u'0.88', u'0.83', u'0.87', u'2/1748', u'21050', u'8'], [u'124069']]

discovery = {
    'loads': [(None, 'cpuload_default_levels')],
    'threads': [(None, {})],
}

checks = {
    'loads': [(
        None,
        (5.0, 10.0),
        [(
            0,
            '15 min load: 0.87 at 8 Cores (0.11 per Core)',
            [
                ('load1', 0.88, 40.0, 80.0, 0, 8),
                ('load5', 0.83, 40.0, 80.0, 0, 8),
                ('load15', 0.87, 40.0, 80.0, 0, 8),
            ],
        )],
    )],
    'threads': [(
        None,
        {
            'levels': (2000, 4000)
        },
        [
            (0, 'Count: 1748 threads', [('threads', 1748, 2000.0, 4000.0, None, None)]),
            (0, 'Usage: 1.41%', [('thread_usage', 1.408893438328672, None, None, None, None)]),
        ],
    )],
}
