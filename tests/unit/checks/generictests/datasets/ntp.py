# yapf: disable


checkname = 'ntp'


info = [['-',
         '42.202.61.100',
         '.INIT.',
         '16',
         'u',
         '-',
         '1024',
         '0',
         '0.000',
         '0.000',
         '0.000']]


discovery = {'': [], 'time': [(None, {})]}


checks = {'time': [(None,
                    {'alert_delay': (300, 3600), 'ntp_levels': (10, 200.0, 500.0)},
                    [(0, 'found 1 peers, but none is suitable', []),
                     (0, 'just started monitoring', [])])]}