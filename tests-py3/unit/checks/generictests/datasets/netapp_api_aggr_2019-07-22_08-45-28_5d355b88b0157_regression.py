# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = u'netapp_api_aggr'

parsed = {
    u'aggr1': {
        u'size-total': u'43025357561856',
        u'size-available': u'8721801302016',
        u'aggregation': u'aggr1'
    },
    u'aggr2': {
        u'aggregation': u'aggr2'
    }
}

discovery = {'': [(u'aggr1', {})]}

checks = {
    '': [
        (
            u'aggr1', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    0, '79.73% used (31.20 of 39.13 TB)', [
                        (
                            u'aggr1', 32714420.56640625, 32825742.76875,
                            36928960.61484375, 0, 41032178.4609375
                        ),
                        ('fs_size', 41032178.4609375, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
