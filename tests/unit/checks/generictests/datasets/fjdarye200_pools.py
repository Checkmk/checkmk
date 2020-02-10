# -*- encoding: utf-8
# yapf: disable
checkname = 'fjdarye200_pools'

info = [[u'0', u'117190584', u'105269493']]

discovery = {'': [('0', {})]}

checks = {
    '': [
        (
            '0', {
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
                    1,
                    '89.83% used (100.39 of 111.76 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            '0', 105269493, 93752467.2, 105471525.6, 0,
                            117190584
                        ), ('fs_size', 117190584, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
