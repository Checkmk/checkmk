# yapf: disable


checkname = 'enterasys_powersupply'


info = [[u'101', u'3', u'1', u'1'],
        [u'102', u'2', u'1', u'1'],
        [u'201', u'3', u'1', u'1'],
        [u'202', u'3', u'1', u'1'],
        [u'301', u'3', u'1', u'1'],
        [u'302', u'3', u'1', u'1'],
        [u'401', u'3', u'1', u'1'],
        [u'402', u'', u'', u'1']]


discovery = {'': [(u'101', {}),
                  (u'201', {}),
                  (u'202', {}),
                  (u'301', {}),
                  (u'302', {}),
                  (u'401', {})]}


checks = {'': [(u'101',
                {'redundancy_ok_states': [1]},
                [(0, 'PSU working and redundant (ac-dc)', [])]),
               (u'201',
                {'redundancy_ok_states': [1]},
                [(0, 'PSU working and redundant (ac-dc)', [])]),
               (u'202',
                {'redundancy_ok_states': [1]},
                [(0, 'PSU working and redundant (ac-dc)', [])]),
               (u'301',
                {'redundancy_ok_states': [1]},
                [(0, 'PSU working and redundant (ac-dc)', [])]),
               (u'302',
                {'redundancy_ok_states': [1]},
                [(0, 'PSU working and redundant (ac-dc)', [])]),
               (u'401',
                {'redundancy_ok_states': [1]},
                [(0, 'PSU working and redundant (ac-dc)', [])])]}