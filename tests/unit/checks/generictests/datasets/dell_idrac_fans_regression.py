# -*- encoding: utf-8
# yapf: disable


checkname = 'dell_idrac_fans'


info = [[u'1', u'1', u'', u'System Board Fan1A', u'', u'', u'', u''],
        [u'2', u'2', u'', u'System Board Fan1B', u'', u'', u'', u''],
        [u'3', u'10', u'', u'System Board Fan2A', u'', u'', u'', u'']]


discovery = {'': [(u'3', {})]}


checks = {'': [(u'3', {}, [(2, u'Status: FAILED, Name: System Board Fan2A', [])])]}