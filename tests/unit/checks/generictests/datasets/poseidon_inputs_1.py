

checkname = 'poseidon_inputs'


info = [[u'1', u'Bezeichnung Eingang 1', u'1', u'0'],
        [u'0', u'Bezeichnung Eingang 2', u'2', u'0'],
        [u'0', u'Bezeichnung Eingang 3', u'1', u'1'],
        [u'0', u'Bezeichnung Eingang 4', u'1', u'1'],
        [u'0', u'Comm Monitor 1', u'0', u'0']]


discovery = {'': [(u'Bezeichnung Eingang 1', {}),
                  (u'Bezeichnung Eingang 2', {}),
                  (u'Bezeichnung Eingang 3', {}),
                  (u'Bezeichnung Eingang 4', {}),
                  (u'Comm Monitor 1', {})]}


checks = {'': [(u'Bezeichnung Eingang 1',
                'default',
                [(0, u'Bezeichnung Eingang 1: AlarmSetup: activeOff', []),
                 (0, 'Alarm State: normal', []),
                 (0, 'Values on', [])]),
               (u'Bezeichnung Eingang 2',
                'default',
                [(0, u'Bezeichnung Eingang 2: AlarmSetup: activeOn', []),
                 (0, 'Alarm State: normal', []),
                 (0, 'Values off', [])]),
               (u'Bezeichnung Eingang 3',
                'default',
                [(0, u'Bezeichnung Eingang 3: AlarmSetup: activeOff', []),
                 (2, 'Alarm State: alarm', []),
                 (0, 'Values off', [])]),
               (u'Bezeichnung Eingang 4',
                'default',
                [(0, u'Bezeichnung Eingang 4: AlarmSetup: activeOff', []),
                 (2, 'Alarm State: alarm', []),
                 (0, 'Values off', [])]),
               (u'Comm Monitor 1',
                'default',
                [(0, u'Comm Monitor 1: AlarmSetup: inactive', []),
                 (0, 'Alarm State: normal', []),
                 (0, 'Values off', [])])]}