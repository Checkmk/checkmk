# yapf: disable


checkname = 'ibm_svc_host'


info = [[u'0', u'h_esx01', u'2', u'4', u'degraded'],
        [u'1', u'host206', u'2', u'2', u'online'],
        [u'2', u'host105', u'2', u'2', u'online'],
        [u'3', u'host106', u'2', u'2', u'online']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0, '3 active', []),
                 (0, '0 inactive', [('inactive', 0, None, None, None, None)]),
                 (0, '1 degraded', [('degraded', 1, None, None, None, None)]),
                 (0, '0 offline', [('offline', 0, None, None, None, None)]),
                 (0, '0 other', [('other', 0, None, None, None, None)])])]}