# yapf: disable
checkname = 'df'

info = [[u'C:\\', u'NTFS', u'8192620', u'7724268', u'468352', u'95%', u'C:\\'],
        [u'New_Volume', u'NTFS', u'10240796', u'186256', u'10054540', u'2%', u'E:\\'],
        [u'New_Volume', u'NTFS', u'124929596', u'50840432', u'74089164', u'41%', u'F:\\']]

discovery = {'': [(u'C:/', {}), (u'E:/', {}), (u'F:/', {})]}

checks = {
    '': [
        (u'C:/', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        },
         [(2, '94.28% used (7.37 of 7.81 GB), (warn/crit at 80.0%/90.0%), trend: 0.00 B / 24 hours',
           [(u'C:/', 7543.23046875, 6400.484375, 7200.544921875, 0, 8000.60546875),
            ('fs_size', 8000.60546875, None, None, None, None),
            ('growth', 0.0, None, None, None, None), ('trend', 0, None, None, 0,
                                                      333.3585611979167)])]),
        (u'New_Volume E:/', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        }, [(0, '1.82% used (181.89 MB of 9.77 GB), trend: 0.00 B / 24 hours',
             [(u'E:/', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
              ('fs_size', 10000.77734375, None, None, None, None),
              ('growth', 0.0, None, None, None, None), ('trend', 0, None, None, 0,
                                                        416.6990559895833)])]),
        (u'E:/', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        }, [(0, '1.82% used (181.89 MB of 9.77 GB), trend: 0.00 B / 24 hours',
             [(u'E:/', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
              ('fs_size', 10000.77734375, None, None, None, None),
              ('growth', 0.0, None, None, None, None), ('trend', 0, None, None, 0,
                                                        416.6990559895833)])]),
        (u'F:/', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        }, [(0, '40.7% used (48.49 of 119.14 GB), trend: 0.00 B / 24 hours',
             [(u'F:/', 49648.859375, 97601.246875, 109801.402734375, 0, 122001.55859375),
              ('fs_size', 122001.55859375, None, None, None, None),
              ('growth', 0.0, None, None, None, None), ('trend', 0, None, None, 0,
                                                        5083.398274739583)])]),
    ]
}
