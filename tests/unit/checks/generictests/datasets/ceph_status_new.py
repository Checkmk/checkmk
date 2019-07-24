# yapf: disable


checkname = 'ceph_status'


info = [['{'],
        ['"fsid":', '"123-abc-456",'],
        ['"health":', '{'],
        ['"checks":', '{},'],
        ['"status":', '"HEALTH_OK",'],
        ['"summary":', '['],
        ['{'],
        ['"severity":', '"HEALTH_WARN",'],
        ['"summary":',
         '"\'ceph',
         "health'",
         'JSON',
         'format',
         'has',
         'changed',
         'in',
         'luminous.',
         'If',
         'you',
         'see',
         'this',
         'your',
         'monitoring',
         'system',
         'is',
         'scraping',
         'the',
         'wrong',
         'fields.',
         'Disable',
         'this',
         'with',
         "'mon",
         'health',
         'preluminous',
         'compat',
         'warning',
         '=',
         'false\'"'],
        ['}'],
        ['],'],
        ['"overall_status":', '"HEALTH_WARN"'],
        ['},'],
        ['"election_epoch":', '2020'],
        ['}']]


discovery = {'': [(None, {})], 'mgrs': [], 'osds': [], 'pgs': []}


checks = {'': [(None,
                {'epoch': (1, 3, 30)},
                [(0, 'Health: OK', []), (0, 'Epoch: 0/30 m', [])])]}
