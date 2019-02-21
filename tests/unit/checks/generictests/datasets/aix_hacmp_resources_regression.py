# yapf: disable
checkname = 'aix_hacmp_resources'

info = [
    [
        'pdb213rg', 'ONLINE', 'pasv0450', 'non-concurrent', 'OHN', 'FNPN', 'NFB', 'ignore', '', '',
        ' ', ' ', '', '', ''
    ],
    [
        'pdb213rg', 'OFFLINE', 'pasv0449', 'non-concurrent', 'OHN', 'FNPN', 'NFB', 'ignore', '', '',
        ' ', ' ', '', '', ''
    ],
    [
        'pmon01rg', 'ONLINE', 'pasv0449', 'non-concurrent', 'OHN', 'FNPN', 'NFB', 'ignore', '', '',
        ' ', ' ', '', '', ''
    ],
    [
        'pmon01rg', 'OFFLINE', 'pasv0450', 'non-concurrent', 'OHN', 'FNPN', 'NFB', 'ignore', '', '',
        ' ', ' ', '', '', ''
    ],
]

discovery = {'': [('pdb213rg', None), ('pmon01rg', None)]}

checks = {
    '': [
        ('pdb213rg', {
            'expect_online_on': 'first'
        }, [(0, 'online on node pasv0450, offline on node pasv0449', [])]),
        ('pmon01rg', {
            'expect_online_on': 'first'
        }, [(0, 'online on node pasv0449, offline on node pasv0450', [])]),
    ]
}
