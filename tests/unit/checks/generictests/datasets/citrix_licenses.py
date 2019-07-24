# -*- encoding: utf-8
# yapf: disable


checkname = 'citrix_licenses'


info = [['PVS_STD_CCS', '80', '90'],
        ['PVS_STD_CCS', '22', '9'],
        ['CEHV_ENT_CCS', '22', '0'],
        ['MPS_ENT_CCU', '2160', '1636'],
        ['MPS_ENT_CCU', '22', '22'],
        ['XDT_ENT_UD', '22', '23'],
        ['XDS_ENT_CCS', '22', '0'],
        ['PVSD_STD_CCS', '42', '40']]


discovery = {'': [('CEHV_ENT_CCS', None),
                  ('MPS_ENT_CCU', None),
                  ('PVSD_STD_CCS', None),
                  ('PVS_STD_CCS', None),
                  ('XDS_ENT_CCS', None),
                  ('XDT_ENT_UD', None)]}


checks = {'': [('CEHV_ENT_CCS',
                None,
                [(0, 'used 0 out of 22 licenses', [('licenses', 0, 22, 22, 0, 22)])]),
               ('MPS_ENT_CCU',
                {},
                [(0,
                  'used 1658 out of 2182 licenses',
                  [('licenses', 1658, 2182, 2182, 0, 2182)])]),
               ('PVSD_STD_CCS',
                (10.0, 0.0),
                [(1, 'used 40 out of 42 licenses (warn/crit at 37/42)', [('licenses', 40, 37.800000000000004, 42, 0, 42)])]),
               ('PVS_STD_CCS',
                (5, 0),
                [(1,
                  'used 99 out of 102 licenses (warn/crit at 97/102)',
                  [('licenses', 99, 97, 102, 0, 102)])]),
               ('XDS_ENT_CCS',
                {},
                [(0, 'used 0 out of 22 licenses', [('licenses', 0, 22, 22, 0, 22)])]),
               ('XDT_ENT_UD',
                {},
                [(2,
                  'used 23 licenses, but you have only 22 (warn/crit at 22/22)',
                  [('licenses', 23, 22, 22, 0, 22)])])]}
