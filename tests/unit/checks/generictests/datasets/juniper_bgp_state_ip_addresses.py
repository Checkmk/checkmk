checkname = 'juniper_bgp_state'

info = [
    [u'4', u'1', 'DE AD BE EF 00 40 01 11 00 00 00 00 00 00 00 01'],
    [u'4', u'2', '00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'],
    [u'4', u'2', 'DE AD BE EF 00 40 01 11 00 00 00 00 00 00 00 00'],
    [u'4', u'1', '00 00 00 00 00 40 01 11 00 00 10 0A 00 00 00 00'],
    [u'5', u'2', 'this is not a valid IP'],
]

discovery = {
    '': [
        (u'[dead:beef:40:111::1]', {}), (u'[::]', {}),
        (u'[dead:beef:40:111::]', {}), (u'[::40:111:0:100a:0:0]', {}),
        (u"'this is not a valid IP'", {}),
        ]
}

checks = {
    '': [
        (u'[dead:beef:40:111::1]', 'default',
         [(0, u'Status with peer [dead:beef:40:111::1] is opensent', []),
          (1, 'operational status: halted', [])]),
        (u'[::]', 'default',
         [(2, u'Status with peer [::] is opensent', []),
          (0, 'operational status: running', [])]),
        (u'[dead:beef:40:111::]', 'default',
         [(2, u'Status with peer [dead:beef:40:111::] is opensent', []),
          (0, 'operational status: running', [])]),
        (u'[::40:111:0:100a:0:0]', 'default',
         [(0, u'Status with peer [::40:111:0:100a:0:0] is opensent', []),
          (1, 'operational status: halted', [])]),
        (u"'this is not a valid IP'", 'default',
         [(2, u"Status with peer 'this is not a valid IP' is openconfirm", []),
          (0, 'operational status: running', [])]),
    ]
}
