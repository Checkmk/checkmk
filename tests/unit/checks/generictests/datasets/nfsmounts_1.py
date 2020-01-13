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
        ('/path/to/share3', {}, [(2, 'Unknown state: drunk', [])]),
        (
            '/path/to/share4', {}, [
                (0, '55.77% used (27.43 of 49.18 GB), trend: 0.00 B / 24 hours', []),
            ],
        ),
        (
            '/path/to/share4', {'has_perfdata': True}, [
                (0, '55.77% used (27.43 of 49.18 GB), trend: 0.00 B / 24 hours', [
                    ('fs_used', 29450862592.0, 42248909619.2, 47530023321.6, 0.0, 52811137024.0),
                    ('fs_size', 52811137024.0, None, None, None, None),
                    ('fs_growth', 0.0),
                    ('fs_trend', 0, None, None, 0, 25468.33382716049),
                ]),
            ],
        ),
        (
            '/path/to/share4', {'show_levels': 'on_magic', 'magic': 0.3}, [
                (0, '55.77% used (27.43 of 49.18 GB), trend: 0.00 B / 24 hours', []),
            ],
        ),
    ]
}
