# yapf: disable
checkname = 'raritan_pdu_plugs'

info = [[u'1', u'', u'7'], [u'36', u'FooName', u'7']]

discovery = {
    '': [
        (u'1', {'discovered_state': 'on'}),
        (u'36', {'discovered_state': 'on'}),
    ]
}

checks = {
    '': [
        (u'1', 'on', [
            (0, u'Status: on', []),
        ]),
        (u'36', 'on', [
            (0, u'FooName', []),
            (0, u'Status: on', []),
        ]),
        (u'1', 'on', [
            (0, u'Status: on', []),
            ]),
        (u'36', 5, [
            (0, u'FooName', []),
            (0, u'Status: on', []),
            (2, u'Expected: above upper warning', []),
        ]),
    ]
}
