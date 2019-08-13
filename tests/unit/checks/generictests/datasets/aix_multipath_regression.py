# -*- encoding: utf-8
# yapf: disable


checkname = 'aix_multipath'


info = [[u'hdisk0', u'vscsi0', u'Enabled'],
        [u'hdisk1', u'fscsi0', u'Enabled'],
        [u'hdisk1', u'fscsi1', u'Enabled'],
        [u'hdisk2', u'fscsi0', u'Enabled'],
        [u'hdisk2', u'fscsi1', u'Missing'],
        [u'hdisk2', u'fscsi3', u'Enabled'],
        [u'hdisk2', u'fscsi4', u'Enabled'],
        [u'hdisk3', u'fscsi1', u'Missing'],
        [u'hdisk3', u'fscsi2', u'Missing'],
        [u'hdisk3', u'fscsi3', u'Missing'],
        [u'hdisk3', u'fscsi4', u'Enabled'],
        [u'hdisk3', u'fscsi5', u'Enabled'],
        [u'hdisk3', u'fscsi6', u'Enabled']]


discovery = {'': [(u'hdisk0', {'paths': 1}),
                  (u'hdisk1', {'paths': 2}),
                  (u'hdisk2', {'paths': 4}),
                  (u'hdisk3', {'paths': 6})]}


checks = {'': [(u'hdisk0', {'paths': 1}, [(0, '1 paths total', [])]),
               (u'hdisk1', {'paths': 2}, [(0, '2 paths total', [])]),
               (u'hdisk2',
                {'paths': 4},
                [(1, '1 paths not enabled (!), 4 paths total', [])]),
               (u'hdisk3',
                {'paths': 6},
                [(1, '3 paths not enabled (!), 6 paths total', [])]),
               ]}
