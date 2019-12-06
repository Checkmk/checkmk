# -*- encoding: utf-8
# yapf: disable
checkname = 'nfsmounts'

info = [
    ['/path/to/share1', 'hanging', '1611668', '794767', '712899', '32768'],
    ['/path/to/share2', 'ok', '-', '-', '-', '-'],
    ['/path/to/share3', 'drunk', '1611668', '794767', '712899', '32768'],
    ['/path/to/share4', 'ok', '1611668', '794767', '712899', '32768']
]

discovery = {
    '': [
        ('/path/to/share1', {}), ('/path/to/share2', {}),
        ('/path/to/share3', {}), ('/path/to/share4', {})
    ]
}

checks = {
    '': [
        ('/path/to/share1', {}, [(2, 'Server not responding', [])]),
        ('/path/to/share2', {}, [(0, 'Mount seems OK', [])]),
        ('/path/to/share3', {}, [(2, 'Unknown state', [])]),
        (
            '/path/to/share4', {}, [
                (0, '55.8% used (27.43 GB of 49.18 GB)', []),
            ],
        ),
        (
            '/path/to/share4', {'has_perfdata': True}, [
                (0, '55.8% used (27.43 GB of 49.18 GB)', [
                    ('fs_size', 52811137024),
                    ('fs_used', 29450862592),
                ]),
            ],
        ),
    ]
}
