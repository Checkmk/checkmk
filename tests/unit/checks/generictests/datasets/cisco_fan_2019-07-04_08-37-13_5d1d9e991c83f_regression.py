# -*- encoding: utf-8
# yapf: disable


checkname = u'cisco_fan'


info = [[u'Fan_1_rpm', u'', u'0'],
        [u'Fan_2_rpm', u'1', u'1'],
        [u'Fan_3_rpm', u'999', u'2']]


discovery = {'': [(u'Fan_2_rpm 1', None)]}


checks = {'': [(u'Fan_2_rpm 1', {}, [(0, u'Status: normal', [])])]}
