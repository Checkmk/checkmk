checkname = 'juniper_bgp_state'

info = [
    [u'6', u'2', '64 60 01 22'],
    [u'3', u'2', '64 60 01 26'],
]

discovery = {
    '': [(u'100.96.1.34', {}), (u'100.96.1.38', {}),
        ]
}

checks = {
    '': [
        (u'100.96.1.34', 'default',
         [(0, u'Status with peer 100.96.1.34 is established', []),
          (0, 'operational status: running', [])]),
        (u'100.96.1.38', 'default',
         [(2, u'Status with peer 100.96.1.38 is active', []),
          (0, 'operational status: running', [])]),
    ]
}
