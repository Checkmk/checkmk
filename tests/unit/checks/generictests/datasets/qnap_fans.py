# -*- encoding: utf-8


# yapf: disable

checkname = 'qnap_fans'

info = [[u'1', u'1027 RPM'], [u'2', u'968 RPM']]

discovery = {'':[(u'1',{}),(u'2',{})]}

checks = {'': [
('1', {}, [(0, u"Speed: 1027 RPM", None)]),
('2', {}, [(0, u"Speed: 968 RPM", None)]),
] }
