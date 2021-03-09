# -*- encoding: utf-8
# yapf: disable


checkname = 'sap_hana_ess'


info = [[u'[[H11 11]]'], [u'started', u'0'], [u'active', u'yes']]


discovery = {'': [(u'H11 11', {})]}


checks = {'': [(u'H11 11',
                {},
                [(0, u'Active status: yes', []),
                 (2, 'Started threads: 0', [('threads', 0, None, None, None, None)])])]}