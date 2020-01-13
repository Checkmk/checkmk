# -*- encoding: utf-8
# yapf: disable
checkname = 'brocade_fcport'

info = [
    [
        [
            u'1', u'4', u'2', u'2', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'15', u'5', u'del_EVA6000_A2'
        ],
        [
            u'2', u'6', u'1', u'1', u'1215057779', u'3341142793',
            u'2315846346', u'3778522298', u'2869057944', u'0', u'0', u'6',
            u'0', u'4', u'ISL_fswf01_Port_1'
        ],
        [
            u'3', u'4', u'2', u'2', u'9770', u'3220', u'675', u'135', u'0',
            u'0', u'0', u'3', u'0', u'5', u'del_fsvdb06_R'
        ],
        [
            u'4', u'6', u'1', u'1', u'1766254627', u'4035913760', u'344812533',
            u'195005757', u'0', u'0', u'72', u'22486', u'47', u'4',
            u'fsvmg01_R'
        ]
    ], [[u'2', u'64'], [u'24', u'64']],
    [
        [u'805306369', u'6', u'100'], [u'805306370', u'24', u'0'],
        [u'805306371', u'131', u'0'], [u'805306372', u'1', u'0'],
        [u'805306373', u'1', u'0'], [u'805306374', u'1', u'0'],
        [u'1073741824', u'56', u'8000'], [u'1073741825', u'56', u'4000'],
        [u'1073741826', u'56', u'8000'], [u'1073741827', u'56', u'4000']
    ],
    [
        [
            u'16.0.0.5.30.93.171.142.0.0.0.0.0.0.0.0.1',
            u'00 00 00 00 00 00 00 00', u'00 00 00 00 00 00 00 00',
            u'00 00 00 03 74 88 FB 00', u'00 00 00 03 20 A6 03 B8',
            u'00 00 00 00 00 00 00 00'
        ],
        [
            u'16.0.0.5.30.93.171.142.0.0.0.0.0.0.0.0.2',
            u'00 00 00 0C 8F 70 DD 74', u'00 00 00 02 E2 EC 57 2B',
            u'00 00 5B B6 AF 3C F8 34', u'00 00 13 9F 3C EC EB 9C',
            u'00 00 00 00 AB 11 63 B9'
        ],
        [
            u'16.0.0.5.30.93.171.142.0.0.0.0.0.0.0.0.3',
            u'00 00 00 00 00 00 02 A3', u'00 00 00 00 00 00 00 87',
            u'00 00 00 00 00 00 98 A8', u'00 00 00 00 00 00 32 50',
            u'00 00 00 00 00 00 00 00'
        ],
        [
            u'16.0.0.5.30.93.171.142.0.0.0.0.0.0.0.0.4',
            u'00 00 00 08 14 8D FC 23', u'00 00 00 08 0B 9F D9 BB',
            u'00 00 00 05 A5 3F 0E 84', u'00 00 00 03 C2 50 E5 20',
            u'00 00 00 00 00 00 00 00'
        ]
    ]
]

discovery = {
    '': [
        (
            u'1 ISL ISL_fswf01_Port_1',
            '{ "phystate": [6], "opstate": [1], "admstate": [1] }'
        ),
        (
            u'3 fsvmg01_R',
            '{ "phystate": [6], "opstate": [1], "admstate": [1] }'
        )
    ]
}

checks = {
    '': [
        (
            u'1 ISL ISL_fswf01_Port_1', {
                'assumed_speed': 2.0,
                'phystate': [6],
                'notxcredits': (3.0, 20.0),
                'opstate': [1],
                'c3discards': (3.0, 20.0),
                'admstate': [1],
                'rxencinframes': (3.0, 20.0),
                'rxcrcs': (3.0, 20.0),
                'rxencoutframes': (3.0, 20.0)
            }, [
                (
                    0,
                    'ISL speed: 4 Gbit/s, In: 0.00 B/s, Out: 0.00 B/s, Physical: in sync, Operational: online, Administrative: online',
                    [
                        ('in', 0.0, None, None, 0, 400000000.0),
                        ('out', 0.0, None, None, 0, 400000000.0),
                        ('rxframes', 0.0, None, None, None, None),
                        ('txframes', 0.0, None, None, None, None),
                        ('rxcrcs', 0.0, None, None, None, None),
                        ('rxencoutframes', 0.0, None, None, None, None),
                        ('rxencinframes', 0.0, None, None, None, None),
                        ('c3discards', 0.0, None, None, None, None),
                        ('notxcredits', 0.0, None, None, None, None),
                        ('fc_bbcredit_zero', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'3 fsvmg01_R', {
                'assumed_speed': 2.0,
                'phystate': [6],
                'notxcredits': (3.0, 20.0),
                'opstate': [1],
                'c3discards': (3.0, 20.0),
                'admstate': [1],
                'rxencinframes': (3.0, 20.0),
                'rxcrcs': (3.0, 20.0),
                'rxencoutframes': (3.0, 20.0)
            }, [
                (
                    0,
                    'Speed: 4 Gbit/s, In: 0.00 B/s, Out: 0.00 B/s, Physical: in sync, Operational: online, Administrative: online',
                    [
                        ('in', 0.0, None, None, 0, 400000000.0),
                        ('out', 0.0, None, None, 0, 400000000.0),
                        ('rxframes', 0.0, None, None, None, None),
                        ('txframes', 0.0, None, None, None, None),
                        ('rxcrcs', 0.0, None, None, None, None),
                        ('rxencoutframes', 0.0, None, None, None, None),
                        ('rxencinframes', 0.0, None, None, None, None),
                        ('c3discards', 0.0, None, None, None, None),
                        ('notxcredits', 0.0, None, None, None, None),
                        ('fc_bbcredit_zero', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
