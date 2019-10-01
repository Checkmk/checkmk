# -*- encoding: utf-8
# yapf: disable


checkname = 'emc_isilon_quota'


info = [[u'/ifs/data/pacs',
         u'0',
         u'1',
         u'219902325555200',
         u'0',
         u'0',
         u'3844608548041']]


discovery = {'': [(u'/ifs/data/pacs', {})]}


checks = {'': [(u'/ifs/data/pacs',
                {},
                [(0,
                  '1.75% used (3.50 of 200.00 TB), trend: 0.00 B / 24 hours',
                  [(u'/ifs/data/pacs',
                    3666504.428902626,
                    167772160.0,
                    209715200.0,
                    0,
                    209715200.0),
                   ('fs_size', 209715200.0, None, None, None, None),
                   ('growth', 0.0, None, None, None, None),
                   ('trend', 0, None, None, 0, 8738133.333333334)])])]}