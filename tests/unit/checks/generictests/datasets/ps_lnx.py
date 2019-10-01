# -*- encoding: utf-8
# yapf: disable


checkname = 'ps'


info = []


extra_sections = {
    '': [[
            ['NODE', '[header]', 'CGROUP', 'USER', 'VSZ', 'RSS', 'TIME', 'ELAPSED', 'PID', 'COMMAND'],
            ['NODE', '1:name=systemd:/init.scope,', 'root', '226036', '9736', '00:00:09', '05:14:30',
             '1', '/sbin/init', '--ladida'],
        ], [], [], [], [], [],
    ],
}


mock_host_conf = {
    '': {'cgroup': ('~.*systemd', False), 'cpu_rescale_max': None, 'descr': 'moooo'},
}


discovery = {
    '': [
        ('moooo', {
            'cgroup': ('~.*systemd', False),
            'cpu_rescale_max': None,
            'match_groups': (),
            'process': None,
            'user': None,
        })
    ],
    'perf': [],
}


checks = {
    '': [
        ('moooo', {
            'cgroup': ('~.*systemd', False),
            'cpu_rescale_max': None,
            'levels': (1, 1, 99999, 99999),
            'match_groups': (),
            'process': None,
            'user': None,
        }, [
            (0, '1 process [running on NODE]', [
                ('count', 1, 100000, 100000, 0, None),
            ]),
            (0, '220.74 MB virtual', [('vsz', 226036, None, None, None, None)]),
            (0, '9.51 MB physical', [('rss', 9736, None, None, None, None)]),
            (0, '0.0% CPU', [('pcpu', 0.0, None, None, None, None)]),
            (0, 'running for 314 m', []),
        ])
    ],
}
