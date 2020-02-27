# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = '3ware_disks'


info = [[u'p0', u'OK', u'u0', u'465.76', u'GB', u'SATA', u'0', u'-', u'ST3500418AS'],
        [u'p1',
         u'VERIFYING',
         u'u0',
         u'465.76',
         u'GB',
         u'SATA',
         u'1',
         u'-',
         u'ST3500418AS'],
        [u'p2',
         u'SMART_FAILURE',
         u'u0',
         u'465.76',
         u'GB',
         u'SATA',
         u'2',
         u'-',
         u'ST3500320SV'],
        [u'p3',
         u'FOOBAR',
         u'u0',
         u'465.76',
         u'GB',
         u'SATA',
         u'3',
         u'-',
         u'ST3500418AS']]


discovery = {'': [(u'p0', None), (u'p1', None), (u'p2', None), (u'p3', None)]}


checks = {'': [(u'p0',
                {},
                [(0,
                  u'disk status is OK (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)',
                  [])]),
               (u'p1',
                {},
                [(0,
                  u'disk status is VERIFYING (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)',
                  [])]),
               (u'p2',
                {},
                [(1,
                  u'disk status is SMART_FAILURE (unit: u0, size: 465.76,GB, type: SATA, model: ST3500320SV)',
                  [])]),
               (u'p3',
                {},
                [(2,
                  u'disk status is FOOBAR (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)',
                  [])])]}
