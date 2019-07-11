# -*- encoding: utf-8
# yapf: disable


checkname = 'chrony'


info = [[u'506', u'Cannot', u'talk', u'to', u'daemon']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'alert_delay': (300, 3600), 'ntp_levels': (10, 200.0, 500.0)},
                [(2, u'506 Cannot talk to daemon', [])])]}