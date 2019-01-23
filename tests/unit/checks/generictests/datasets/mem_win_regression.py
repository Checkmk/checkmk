

checkname = 'mem'


info = [
    ['MemTotal:', '33553908', 'kB'],
    ['MemFree:', '16791060', 'kB'],
    ['SwapTotal:', '65536000', 'kB'],
    ['SwapFree:', '62339136', 'kB'],
    ['PageTotal:', '99089908', 'kB'],
    ['PageFree:', '79130196', 'kB'],
    ['VirtualTotal:', '2097024', 'kB'],
    ['VirtualFree:', '2055772', 'kB'],
]


discovery = {'linux': [], 'used': [], 'vmalloc': [], 'win': [(None, {})]}


checks = {
    'win': [
        (None, {'memory': (80.0, 90.0), 'pagefile': (80.0, 90.0)}, [
            (0, 'Memory usage: 50.0% (16.0/32.0 GB)', [
                ('memory', 16369.96875, 26213.990625, 29490.739453125, 0, 32767.48828125),
                ('mem_total', 32767.48828125, None, None, None, None),
            ]),
            (0, 'Commit Charge: 20.1% (19.0/94.5 GB)', [
                ('pagefile', 19491.90625, 77413.990625, 87090.739453125, 0, 96767.48828125),
                ('pagefile_total', 96767.48828125, None, None, None, None),
            ]),
        ]),
        (None, {'memory': (6553, 3277), 'pagefile': (19492, 77414)}, [
            (0, 'Memory usage: 50.0% (16.0/32.0 GB)', [
                ('memory', 16369.96875, 6553, 3277, 0, 32767.48828125),
                ('mem_total', 32767.48828125, None, None, None, None),
            ]),
            (2, 'Commit Charge: 20.1% (19.0/94.5 GB)', [
                ('pagefile', 19491.90625, 19492.0, 77414.0, 0, 96767.48828125),
                ('pagefile_total', 96767.48828125, None, None, None, None),
            ]),
        ]),
    ],
}
