checkname = 'juniper_bgp_state'

info = [
    [u'6.1.80.81.193.134.1.80.81.192.3', u'6', u'2'],
    [u'6.1.80.81.193.134.1.80.81.192.24', u'3', u'2'],
]

discovery = {
    '': [(u'80.81.192.24', {}), (u'80.81.192.3', {}),
        ]
}

checks = {
    '': [
        (u'80.81.192.24', 'default',
         [(2, u'Status with peer 80.81.192.24 is active', []),
          (0, 'operational status: running', [])]),
        (u'80.81.192.3', 'default',
         [(0, u'Status with peer 80.81.192.3 is established', []),
          (0, 'operational status: running', [])]),
    ]
}
