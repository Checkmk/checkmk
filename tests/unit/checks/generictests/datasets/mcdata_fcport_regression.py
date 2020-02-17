# -*- encoding: utf-8
# yapf: disable
checkname = 'mcdata_fcport'

info = [
    [u'1', u'2', u'4',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'2', u'2', u'4',
     u'\x00\x00\x01\x92\xd1\x18rT',
     u'\x00\x00\x00\x00\x1b\xc3\x89\xdc',
     u'\x00\x00\x00\x00\xc6\xe2\xc2\x99',
     u'\x00\x00\x00\x00\x01\xf9\xb9x',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'3', u'2', u'4',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'4', u'1', u'3',
     u'\x00\x00\x00\xce4\xd8\x17}',
     u'\x00\x00\x01-\x0f\x97\x19\x06',
     u'\x00\x00\x00\x00|&\x83\xe9',
     u'\x00\x00\x00\x00\xb3\xe1\x82\x81',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'5', u'1', u'3',
     u'\x00\x00\x00\x00\x00\x00\x01\xc3',
     u'\x00\x00\x00\x00\x00\x00\x06;',
     u'\x00\x00\x00\x00\x00\x00\x00\x14',
     u'\x00\x00\x00\x00\x00\x00\x00r',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'6', u'1', u'3',
     u'\x00\x00\x01f\x14^|\xca',
     u'\x00\x00\x01\x8e\xbeZ\x89\xed',
     u'\x00\x00\x00\x00\xb4\x04\xff\x15',
     u'\x00\x00\x00\x00\xc9\xd0\xe2>',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'7', u'1', u'3',
     u'\x00\x00\x03M]X\x83\xb1',
     u'\x00\x00\x05\x02aR\xec\x97',
     u'\x00\x00\x00\x01\xa59\xc7\xd3',
     u'\x00\x00\x00\x02\x80$"\xe7',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'8', u'2', u'4',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'9', u'2', u'4',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
    [u'10', u'2', u'4',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'\x00\x00\x00\x00\x00\x00\x00\x00',
     u'0'],
]

discovery = {
    '': [
        ('04', "{'state': ['1'], 'speed': 2000000000}"),
        ('05', "{'state': ['1'], 'speed': 2000000000}"),
        ('06', "{'state': ['1'], 'speed': 2000000000}"),
        ('07', "{'state': ['1'], 'speed': 2000000000}"),
    ]
}


freeze_time = "1970-01-01 00:01"


MB = 1024**2

mock_item_state = {
    '': {
        # TODO: this does not seem right. For now, just mock an item state that results in
        #       resonable output values, and debug from here
        'if.in.04': (0.0, 1293046716678129304671667812930467166781293046716678 - 300 * MB),
        'if.inucast.04': (0.0, 3017900673 - 60 * MB),
        'if.innucast.04': (0.0, 0),
        'if.indisc.04': (0.0, 0),
        'if.inerr.04': (0.0, 0),
        'if.out.04': (0.0, 885649839997885649839997885649839997885649839997 - 180 * MB),
        'if.outucast.04': (0.0, 2082898921 - 30 * MB),
        'if.outnucast.04': (0.0, 0),
        'if.outdisc.04': (0.0, 0),
        'if.outerr.04': (0.0, 0),
    },
}

DEFAULT_PARAMS = {
    'state': ['1'],
    'errors': (0.01, 0.1),
    'speed': 2000000000
}

checks = {
    '': [
        ('04', DEFAULT_PARAMS, [
            (0, '[04] (up) 2 Gbit/s, In: 5.00 MB/s (2.1%), Out: 3.00 MB/s (1.3%)', [
                ('in', 5 * MB, None, None, 0, 250000000.0),
                ('inucast', MB, None, None, None, None),
                ('innucast', 0.0, None, None, None, None),
                ('indisc', 0.0, None, None, None, None),
                ('inerr', 0.0, 0.01, 0.1, None, None),
                ('out', 3 * MB, None, None, 0, 250000000.0),
                ('outucast', 0.5 * MB, None, None, None, None),
                ('outnucast', 0.0, None, None, None, None),
                ('outdisc', 0.0, None, None, None, None),
                ('outerr', 0.0, 0.01, 0.1, None, None),
                ('outqlen', 0, None, None, None, None),
            ]),
        ]),
        ('05', DEFAULT_PARAMS, [
            (0, '[05] (up) 2 Gbit/s', [
            ]),
        ]),
    ]
}
