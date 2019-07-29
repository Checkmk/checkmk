# -*- encoding: utf-8
# yapf: disable


checkname = 'ps'


info = [
    [None] + r'(\\DUBETFUTIL502\ntpservice,31108,6140,0,300,2,312500,1250000,105,5,16517) C:\Program Files (x86)\NTP\bin\ntpd.exe -U 3 -M -c C:\Program Files (x86)\NTP\etc\ntp.conf'.split(),
]


discovery = {
    '': [
        ('NTP', {'process': '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*', 'cpu_rescale_max': None, 'match_groups': (None, 'NTP'), 'user': None})],
    'perf': [],
}


mock_host_conf = {
        '': {"descr": '%1%2', "match": '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*'}
}

extra_sections = {
    '': [[], [], [], [], [], []],
}


checks = {
    '': [
        (u'NTP', {
            'process': '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
            'match_groups': [None, u'NTP'],  # used to be a list prior to 1.5.0p20, so we need to be able to deal with it
            'levels': (1, 1, 1, 1),
            'user': None,
            'cpu_rescale_max': None,
        }, [
            (0, '1 process', [('count', 1, 2, 2, 0)]),
            (0, '30.38 MB virtual', [('vsz', 31108)]),
            (0, '6.00 MB physical', [('rss', 6140)]),
            (0, '0.0% CPU', [('pcpu', 0.0)]),
            (0, '105 process handles', [('process_handles', 105)]),
            (0, 'running for 275 m', []),
        ]),
    ],
}
