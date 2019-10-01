# -*- encoding: utf-8
# yapf: disable


checkname = u'netapp_api_aggr'


parsed = {u'aggr1': {u'aggregation': u'aggr1',
                     u'size-available': u'8721801302016',
                     u'size-total': u'43025357561856'},
          u'aggr2': {u'aggregation': u'aggr2'}}


discovery = {'': [(u'aggr1', {})]}


checks = {'': [(u'aggr1',
                {'inodes_levels': (10.0, 5.0),
                 'levels': (80.0, 90.0),
                 'levels_low': (50.0, 60.0),
                 'magic_normsize': 20,
                 'show_inodes': 'onlow',
                 'show_levels': 'onmagic',
                 'show_reserved': False,
                 'trend_perfdata': True,
                 'trend_range': 24},
                [(0,
                  '79.73% used (31.20 of 39.13 TB), trend: 0.00 B / 24 hours',
                  [(u'aggr1',
                    32714420.56640625,
                    32825742.76875,
                    36928960.61484375,
                    0,
                    41032178.4609375),
                   ('fs_size', 41032178.4609375, None, None, None, None),
                   ('growth', 0.0, None, None, None, None),
                   ('trend', 0, None, None, 0, 1709674.1025390625)])])]}
