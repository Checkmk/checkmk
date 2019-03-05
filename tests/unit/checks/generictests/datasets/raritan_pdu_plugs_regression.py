# yapf: disable
checkname = 'raritan_pdu_plugs'

info = [[u'1', u'', u'7'], [u'36', u'FooName', u'7']]

discovery = {
    '': [
        (u'1', 7),
        (u'36', 7),
    ]
}

checks = {
    '': [
        (u'1', 7, [
            (0, u'Status: on', []),
        ]),
        (u'36', 7, [
            (0, u'FooName', []),
            (0, u'Status: on', []),
        ]),
        (u'1', 'on', [
            (0, u'Status: on', []),
            ]),
        (u'36', 5, [
            (0, u'FooName', []),
            (2, u'Status: on', []),
        ]),
    ]
}
