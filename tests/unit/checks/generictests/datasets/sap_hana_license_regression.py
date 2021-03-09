# -*- encoding: utf-8
# yapf: disable


checkname = 'sap_hana_license'


info = [[None, u'[[Y04 10]]'],
        [None,
         u'TRUE',
         u'FALSE',
         u'FALSE',
         u'33',
         u'147',
         u'TRUE',
         u'2020-08-02 23:59:59.999999000'],
        [None, u'[[H62 10]]'],
        [None, u'FALSE', u'TRUE', u'FALSE', u'19', u'12300', u'TRUE', u'?'],
        [None, u'[[Y04 11]]'],
        [None,
         u'FALSE',
         u'FALSE',
         u'FALSE',
         u'33',
         u'147',
         u'TRUE',
         u'2020-08-02 23:59:59.999999000']]


discovery = {'': [(u'H62 10', {}), (u'Y04 10', {}), (u'Y04 11', {})]}


checks = {'': [(u'H62 10',
                {'license_usage_perc': (80.0, 90.0)},
                [(0, 'Status: unlimited', []), (0, u'License: TRUE', [])]),
               (u'Y04 10',
                {'license_usage_perc': (80.0, 90.0)},
                [(0, 'Size: 33 B', [('license_size', 33, None, None, None, None)]),
                 (0,
                  'Usage: 22.45%',
                  [('license_percentage',
                    22.448979591836736,
                    80.0,
                    90.0,
                    None,
                    None)]),
                 (1, u'License: not FALSE', []),
                 (1, u'Expiration date: 2020-08-02 23:59:59.999999000', [])]),
               (u'Y04 11',
                {'license_usage_perc': (80.0, 90.0)},
                [(0, 'Status: unlimited', []),
                 (1, u'License: not FALSE', []),
                 (1, u'Expiration date: 2020-08-02 23:59:59.999999000', [])])]}