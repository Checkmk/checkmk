# -*- encoding: utf-8
# yapf: disable


checkname = 'emc_isilon_ifs'


info = [[u'615553001652224', u'599743491129344']]


discovery = {'': [('Cluster', None)]}


checks = {'': [('Cluster',
                {},
                [(0,
                  '2.57% used (14.38 of 559.84 TB), trend: 0.00 B / 24 hours',
                  [('ifs', 15077125, 469629670.4, 528333379.2, 0, 587037088),
                   ('fs_size', 587037088, None, None, None, None),
                   ('growth', 0.0, None, None, None, None),
                   ('trend', 0, None, None, 0, 24459878)])])]}