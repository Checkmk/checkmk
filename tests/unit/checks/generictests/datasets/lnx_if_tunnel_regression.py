# -*- encoding: utf-8
# yapf: disable


checkname = 'lnx_if'


info = [[None,
         u'em0',
         u'376716785370 417455222 0 0 0 0 0 0 383578105955 414581956 0 0 0 0 0 0'],
        [None, u'tun0', u'342545566242 0 259949262 0 0 0 0 0  0 19196 0 0  0 0'],
        [None, u'tun1', u'2422824602 0 2357563 0 0 0 0 0  0 0 0 0  0 0'],
        [None, u'[em0]'],
        [None, u'Speed', u' 1000Mb/s'],
        [None, u'Duplex', u' Full'],
        [None, u'Auto-negotiation', u' on'],
        [None, u'Link detected', u' yes'],
        [None, u'Address', u' 00', u'AA', u'11', u'BB', u'22', u'CC'],
        [None, u'[tun0]'],
        [None, u'Link detected', u' yes'],
        [None, u'Address', u' 123'],
        [None, u'[tun1]'],
        [None, u'Link detected', u' yes'],
        [None, u'Address', u' 456']]


discovery = {'': [('1', "{'state': ['1'], 'speed': 1000000000}"),
                  ('2', "{'state': ['1'], 'speed': 0}"),
                  ('3', "{'state': ['1'], 'speed': 0}")]}


checks = {'': [('1',
                {'errors': (0.01, 0.1), 'speed': 1000000000, 'state': ['1']},
                [(0, '[em0] (up) MAC: 00:AA:11:BB:22:CC, 1 Gbit/s', [])]),
               ('2',
                {'errors': (0.01, 0.1), 'speed': 0, 'state': ['1']},
                [(0, '[tun0] (up) speed unknown', [])]),
               ('3',
                {'errors': (0.01, 0.1), 'speed': 0, 'state': ['1']},
                [(0, '[tun1] (up) speed unknown', [])])]}