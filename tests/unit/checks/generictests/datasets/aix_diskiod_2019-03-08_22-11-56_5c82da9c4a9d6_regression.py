# -*- encoding: utf-8
# yapf: disable


checkname = u'aix_diskiod'


info = [[None, u'hdisk0', u'5.1', u'675.7', u'46.5', u'2380130842', u'12130437130'],
        [None, u'hdisk0000', u'58.5', u'19545.1', u'557.3', u'%l', u'%l']]


discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}


checks = {'': [('SUMMARY',
                {},
                [(0,
                  '0.00 B/sec read, 0.00 MB/s, 0.00 B/sec write, 0.00 MB/s',
                  [('read', 0.0, None, None, None, None),
                   ('write', 0.0, None, None, None, None)])])]}