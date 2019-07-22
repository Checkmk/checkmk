# -*- encoding: utf-8
# yapf: disable


checkname = 'fjdarye200_pools'


info = [[u'0', u'117190584', u'105269493']]


discovery = {'': [('0', {})]}


checks = {'': [('0',
                {'inodes_levels': (10.0, 5.0),
                 'levels': (80.0, 90.0),
                 'levels_low': (50.0, 60.0),
                 'magic_normsize': 20,
                 'show_inodes': 'onlow',
                 'show_levels': 'onmagic',
                 'show_reserved': False,
                 'trend_perfdata': True,
                 'trend_range': 24},
                [(1,
                  '89.83% used (100.39 of 111.76 TB), (warn/crit at 80.0%/90.0%), trend: 0.00 B / 24 hours',
                  [('0', 105269493, 93752467.2, 105471525.6, 0, 117190584),
                   ('fs_size', 117190584, None, None, None, None),
                   ('growth', 0.0, None, None, None, None),
                   ('trend', 0, None, None, 0, 4882941)])])]}
