# -*- encoding: utf-8
# yapf: disable


checkname = 'solaris_services'


info = [[u'STATE', u'STIME', u'FMRI'],
        [u'online', u'Jan_1', u'svc1:/cat1/name1:inst1'],
        [u'online', u'Jan_1', u'0:00:00', u'svc2:/cat2/name2:inst2']]


discovery = {'': [], 'summary': [(None, {})]}


checks = {'summary': [(None, {}, [(0, '2 services', []), (0, u'2 online', [])])]}