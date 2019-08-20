# -*- encoding: utf-8
# yapf: disable


checkname = 'hpux_tunables'


info = [[u'Tunable:', u'maxfiles_lim'],
        [u'Usage:', u'152'],
        [u'Setting:', u'63488'],
        [u'Percentage:', u'0.2'],
        [u'Tunable:', u'nkthread'],
        [u'Usage:', u'1314'],
        [u'Setting:', u'8416'],
        [u'Percentage:', u'15.6'],
        [u'Tunable:', u'nproc'],
        [u'Usage:', u'462'],
        [u'Setting:', u'4200'],
        [u'Percentage:', u'11.0'],
        [u'Tunable:', u'semmni'],
        [u'Usage:', u'41'],
        [u'Setting:', u'4200'],
        [u'Percentage:', u'1.0'],
        [u'Tunable:', u'semmns'],
        [u'Usage:', u'1383'],
        [u'Setting:', u'8400'],
        [u'Percentage:', u'16.5'],
        [u'Tunable:', u'shmseg'],
        [u'Usage:', u'3'],
        [u'Setting:', u'512'],
        [u'Percentage:', u'0.6']]


discovery = {'maxfiles_lim': [(None, {})],
             'nkthread': [(None, {})],
             'nproc': [(None, {})],
             'semmni': [(None, {})],
             'semmns': [(None, {})],
             'shmseg': [(None, {})]}


checks = {'maxfiles_lim': [(None,
                            {'levels': (85.0, 90.0)},
                            [(0,
                              '0.24% used (152/63488 files)',
                              [('files', 152, 53964.8, 57139.2, 0, 63488)])])],
          'nkthread': [(None,
                        {'levels': (80.0, 85.0)},
                        [(0,
                          '15.61% used (1314/8416 threads)',
                          [('threads', 1314, 6732.8, 7153.6, 0, 8416)])])],
          'nproc': [(None,
                     {'levels': (90.0, 96.0)},
                     [(0,
                       '11.00% used (462/4200 processes)',
                       [('processes', 462, 3780.0, 4032.0, 0, 4200)])])],
          'semmni': [(None,
                      {'levels': (85.0, 90.0)},
                      [(0,
                        '0.98% used (41/4200 semaphore_ids)',
                        [('semaphore_ids', 41, 3570.0, 3780.0, 0, 4200)])])],
          'semmns': [(None,
                      {'levels': (85.0, 90.0)},
                      [(0,
                        '16.46% used (1383/8400 entries)',
                        [('entries', 1383, 7140.0, 7560.0, 0, 8400)])])],
          'shmseg': [(None,
                      {'levels': (85.0, 90.0)},
                      [(0,
                        '0.59% used (3/512 segments)',
                        [('segments', 3, 435.2, 460.8, 0, 512)])])]}
