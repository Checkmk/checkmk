

checkname = 'juniper_bgp_state'


info = [[u'4',
         u'1',
         [222, 173, 190, 239, 0, 64, 1, 17, 0, 0, 0, 0, 0, 0, 0, 1]],
        [u'4', u'2', [0] * 16],
]


discovery = {'': [('[dead:beef:40:111::1]', {}), ("[::]", {})]}


checks = {'': [('[dead:beef:40:111::1]',
                'default',
                [(0, 'Status with peer [dead:beef:40:111::1] is opensent', []),
                 (1, 'operational status: halted', [])]),
                (u"[::]",
                'default',
                [(2,
                    u"Status with peer [::] is opensent",
                  []),
                 (0, 'operational status: running', [])])]}
