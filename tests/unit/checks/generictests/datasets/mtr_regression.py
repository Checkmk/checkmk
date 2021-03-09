# -*- encoding: utf-8
# yapf: disable
checkname = 'mtr'

info = [
    [
        u'foo.bar.1', u'1578427995', u'2', u'baz-1', u'0.0%', u'10', u'0.3',
        u'0.2', u'0.2', u'0.3', u'0.0', u'???', u'100.0', u'10', u'0.0',
        u'0.0', u'0.0', u'0.0', u'0.0'
    ],
    [
        u'foo.bar.2', u'1578427995', u'2', u'baz-2', u'0.0%', u'10', u'0.3',
        u'0.2', u'0.2', u'0.3', u'0.0', u'???', u'0.0', u'10', u'0.0', u'0.0',
        u'0.0', u'0.0', u'0.0'
    ]
]

discovery = {'': [(u'foo.bar.1', {}), (u'foo.bar.2', {})]}

checks = {
    '': [
        (
            u'foo.bar.1', {
                'rtstddev': (150, 250),
                'rta': (150, 250),
                'pl': (10, 25)
            }, [
                (
                    0, 'Number of Hops: 2', [
                        ('hops', 2, None, None, None, None),
                        ('hop_1_rta', 0.0002, None, None, None, None),
                        ('hop_1_rtmin', 0.0002, None, None, None, None),
                        ('hop_1_rtmax', 0.0003, None, None, None, None),
                        ('hop_1_rtstddev', 0.0, None, None, None, None),
                        (
                            'hop_1_response_time', 0.0003, None, None, None,
                            None
                        ), ('hop_1_pl', 0.0, None, None, None, None)
                    ]
                ),
                (
                    2,
                    u'Packet loss 100.0%(!!) (warn/crit at 10%/25%), Round trip average 0.0ms, Standard deviation 0.0ms\r\nHops in last check:\nHop 1: baz-1\nHop 2: ???\n',
                    [
                        ('hop_1_rta', 0.0002, None, None, None, None),
                        ('hop_1_rtmin', 0.0002, None, None, None, None),
                        ('hop_1_rtmax', 0.0003, None, None, None, None),
                        ('hop_1_rtstddev', 0.0, None, None, None, None),
                        (
                            'hop_1_response_time', 0.0003, None, None, None,
                            None
                        ), ('hop_1_pl', 0.0, None, None, None, None),
                        ('hop_2_rta', 0.0, 0.15, 0.25, None, None),
                        ('hop_2_rtmin', 0.0, None, None, None, None),
                        ('hop_2_rtmax', 0.0, None, None, None, None),
                        ('hop_2_rtstddev', 0.0, 0.15, 0.25, None, None),
                        ('hop_2_response_time', 0.0, None, None, None, None),
                        ('hop_2_pl', 100.0, 10, 25, None, None)
                    ]
                )
            ]
        ),
        (
            u'foo.bar.2', {
                'rtstddev': (150, 250),
                'rta': (150, 250),
                'pl': (10, 25)
            }, [
                (
                    0, 'Number of Hops: 2', [
                        ('hops', 2, None, None, None, None),
                        ('hop_1_rta', 0.0002, None, None, None, None),
                        ('hop_1_rtmin', 0.0002, None, None, None, None),
                        ('hop_1_rtmax', 0.0003, None, None, None, None),
                        ('hop_1_rtstddev', 0.0, None, None, None, None),
                        (
                            'hop_1_response_time', 0.0003, None, None, None,
                            None
                        ), ('hop_1_pl', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0,
                    u'Packet loss 0.0%, Round trip average 0.0ms, Standard deviation 0.0ms\r\nHops in last check:\nHop 1: baz-2\nHop 2: ???\n',
                    [
                        ('hop_1_rta', 0.0002, None, None, None, None),
                        ('hop_1_rtmin', 0.0002, None, None, None, None),
                        ('hop_1_rtmax', 0.0003, None, None, None, None),
                        ('hop_1_rtstddev', 0.0, None, None, None, None),
                        (
                            'hop_1_response_time', 0.0003, None, None, None,
                            None
                        ), ('hop_1_pl', 0.0, None, None, None, None),
                        ('hop_2_rta', 0.0, 0.15, 0.25, None, None),
                        ('hop_2_rtmin', 0.0, None, None, None, None),
                        ('hop_2_rtmax', 0.0, None, None, None, None),
                        ('hop_2_rtstddev', 0.0, 0.15, 0.25, None, None),
                        ('hop_2_response_time', 0.0, None, None, None, None),
                        ('hop_2_pl', 0.0, 10, 25, None, None)
                    ]
                )
            ]
        )
    ]
}
