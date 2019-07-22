# -*- encoding: utf-8
# yapf: disable


checkname = 'fast_lta_volumes'


info = [[u'Archiv_Test', u'1000000000000', u'10000000000'],
        [u'Archiv_Test_1', u'', u'']]


discovery = {'': [(u'Archiv_Test', {})]}


checks = {'': [(u'Archiv_Test',
                {},
                [(0,
                  '1.0% used (9.31 of 931.32 GB), trend: 0.00 B / 24 hours',
                  [(u'Archiv_Test',
                    9536.7431640625,
                    762939.453125,
                    858306.884765625,
                    0,
                    953674.31640625),
                   ('fs_size', 953674.31640625, None, None, None, None),
                   ('growth', 0.0, None, None, None, None),
                   ('trend', 0, None, None, 0, 39736.429850260414)])])]}
