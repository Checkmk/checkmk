checkname = 'juniper_bgp_state'

info = [
    [u'6.1.80.81.193.134.1.80.81.192.3', u'6', u'2'],
    [u'6.1.80.81.193.134.1.80.81.192.24', u'3', u'2'],
]

discovery = {
    '': [(u'80.81.192.24', None), (u'80.81.192.3', None),
        ]
}

checks = {
    '': [
        (u'80.81.192.24', 'default',
         [(2, u'Status with peer 80.81.192.24 is active(!!), operational status: running', [])]),
        (u'80.81.192.3', 'default',
         [(0, u'Status with peer 80.81.192.3 is established, operational status: running', [])]),
    ]
}
