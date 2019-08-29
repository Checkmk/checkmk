# -*- encoding: utf-8
# yapf: disable


checkname = 'dell_compellent_disks'


info = [[[u'1', u'1', u'1', u'', u'1'],
         [u'2', u'999', u'1', u'', u'1'],
         [u'3', u'1', u'999', u'', u'1'],
         [u'4', u'1', u'0', u'ATTENTION', u'1'],
         [u'5', u'1', u'999', u'ATTENTION', u'1']],
        [[u'serial1'], [u'serial2'], [u'serial3'], [u'serial4'], [u'serial5']]]


discovery = {'': [(u'1', None), (u'2', None), (u'3', None), (u'4', None), (u'5', None)]}


checks = {'': [(u'1',
                {},
                [(0, 'Status: UP', []),
                 (0, u'Location: Enclosure 1', []),
                 (0, "Serial number: [u'serial1']", [])]),
               (u'2',
                {},
                [(3, u'Status: unknown[999]', []),
                 (0, u'Location: Enclosure 1', []),
                 (0, "Serial number: [u'serial2']", [])]),
               (u'3',
                {},
                [(0, 'Status: UP', []),
                 (0, u'Location: Enclosure 1', []),
                 (0, "Serial number: [u'serial3']", [])]),
               (u'4',
                {},
                [(0, 'Status: UP', []),
                 (0, u'Location: Enclosure 1', []),
                 (0, "Serial number: [u'serial4']", []),
                 (2, u'Health: not healthy, Reason: ATTENTION', [])]),
               (u'5',
                {},
                [(0, 'Status: UP', []),
                 (0, u'Location: Enclosure 1', []),
                 (0, "Serial number: [u'serial5']", []),
                 (3, u'Health: unknown[999], Reason: ATTENTION', [])])]}