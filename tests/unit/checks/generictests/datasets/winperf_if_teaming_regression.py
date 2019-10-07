# yapf: disable
checkname = 'winperf_if'

info = [
    [u'1476804932.61', u'510', u'2082740'],
    [u'4', u'instances:', u'A_B-C', u'FOO_B-A-R__53', u'A_B-C__3', u'FOO_B-A-R__52'],
    [u'-122', u'246301064630', u'2035719049115', u'191138259305', u'1956798911236', u'bulk_count'],
    [u'-110', u'195002974', u'1888010079', u'157579333', u'1767947062', u'bulk_count'],
    [u'-244', u'81582535', u'531894182', u'42736554', u'450993852', u'bulk_count'],
    [u'-58', u'113420439', u'1356115897', u'114842779', u'1316953210', u'bulk_count'],
    [u'10', u'10000000000', u'1000000000', u'10000000000', u'1000000000', u'large_rawcount'],
    [u'-246', u'85146916834', u'295765890709', u'28180136075', u'244690096455', u'bulk_count'],
    [u'14', u'71520104', u'491241747', u'34804873', u'420107059', u'bulk_count'],
    [u'16', u'10062431', u'40652422', u'7931681', u'30886784', u'bulk_count'],
    [u'18', u'0', u'13', u'0', u'9', u'large_rawcount'],
    [u'20', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'22', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'-4', u'161154147796', u'1739953158406', u'162958123230', u'1712108814781', u'bulk_count'],
    [u'26', u'113162286', u'1355871932', u'114440147', u'1316598654', u'bulk_count'],
    [u'28', u'258153', u'243965', u'402632', u'354556', u'bulk_count'],
    [u'30', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'32', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'34', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1086', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1088', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1090', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1092', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1094', u'0', u'0', u'0', u'0', u'large_rawcount'], [u'[teaming_start]'],
    [
        u'TeamName', u'TeamingMode', u'LoadBalancingAlgorithm', u'MemberMACAddresses',
        u'MemberNames', u'MemberDescriptions', u'Speed', u'GUID'
    ],
    [
        u'T1Team ', u'Lacp ', u'Dynamic ', u'00:00:00:00:00:00;00:00:00:00:00:01',
        u'Ethernet 3;Ethernet 6', u'HP1 Adapter;HP1 Adapter #3', u'10000000000;10000000000',
        u'{123-ABC-456};{FOO-123-BAR}'
    ],
    [
        u'T2Team ', u'Lacp ', u'Dynamic ', u'00:00:00:00:00:02;00:00:00:00:00:03',
        u'Ethernet 7;Ethernet 5', u'HP2 Adapter #52;HP2 Adapter #53', u'1000000000;1000000000',
        u'{BAR-456-BAZ};{1-A-2-B-3-C}'
    ], [u'[teaming_end]'],
    [
        u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus', u'Speed',
        u'GUID'
    ], [u'ABC123 ', u'  ', u' HP2 Adapter ', u' Ethernet ', u' 4 ', u'  ', u' {FOO_XYZ123-BAR}'],
    [u'ABC123 ', u'  ', u' HP2 Adapter ', u' Ethernet 2 ', u' 4 ', u'  ', u' {987-ZYX-654}'],
    [
        u'ABC123 ', u' 00:00:00:00:00:00 ', u' HP1 Adapter ', u' Ethernet 3 ', u' 2 ', u'  ',
        u' {123-ABC-456}'
    ], [u'ABC123 ', u'  ', u' HP1 Adapter ', u' Ethernet 4 ', u' 4 ', u'  ', u' {XYZ-FOO-123}'],
    [
        u'ABC123 ', u' 00:00:00:00:00:01 ', u' HP2 Adapter ', u' Ethernet 5 ', u' 2 ', u'  ',
        u' {1-A-2-B-3-C}'
    ],
    [
        u'ABC123 ', u' 00:00:00:00:00:02 ', u' HP1 Adapter ', u' Ethernet 6 ', u' 2 ', u'  ',
        u' {FOO-123-BAR}'
    ],
    [
        u'ABC123 ', u' 00:00:00:00:00:03 ', u' HP2 Adapter ', u' Ethernet 7 ', u' 2 ', u'  ',
        u' {BAR-456-BAZ}'
    ], [u'ABC123 ', u'  ', u' HP1 Adapter ', u' Ethernet 8 ', u' 4 ', u'  ', u' {FOOBAR-123}'],
    [
        u'ABC123 ', u' 00:00:00:00:00:04 ', u' Microsoft Network Adapter Multiplexor Driver ',
        u' T1Team ', u' 2 ', u' 20000000000 ', u' {456-FOOBAR}'
    ],
    [
        u'ABC123 ', u' 00:00:00:00:00:05 ', u' Microsoft Network Adapter Multiplexor Driver #2 ',
        u' T2Team ', u' 2 ', u' 2000000000 ', u' {FOO-1-BAR-2-BAZ-3}'
    ]
]

discovery = {
    '': [('1', "{'state': ['1'], 'speed': 10000000000}"),
         ('2', "{'state': ['1'], 'speed': 1000000000}"),
         ('3', "{'state': ['1'], 'speed': 10000000000}"),
         ('4', "{'state': ['1'], 'speed': 1000000000}")]
}

checks = {
    '': [('1', {
        'errors': (0.01, 0.1),
        'state': ['1'],
        'speed': 10000000000
    }, [(0, u'[A B-C] (Connected) 10 Gbit/s', [])]),
         ('2', {
             'errors': (0.01, 0.1),
             'state': ['1'],
             'speed': 1000000000
         }, [(0, u'[FOO B-A-R 53] (Connected) 1 Gbit/s', [])]),
         ('3', {
             'errors': (0.01, 0.1),
             'state': ['1'],
             'speed': 10000000000
         }, [(0, u'[A B-C 3] (Connected) 10 Gbit/s', [])]),
         ('4', {
             'errors': (0.01, 0.1),
             'state': ['1'],
             'speed': 1000000000
         }, [(0, u'[FOO B-A-R 52] (Connected) 1 Gbit/s', [])])]
}
