# -*- encoding: utf-8
# yapf: disable
checkname = 'ibm_svc_mdiskgrp'

info = [
    [
        u'0', u'Quorum_2', u'online', u'1', u'0', u'704.00MB', u'64',
        u'704.00MB', u'0.00MB', u'0.00MB', u'0.00MB', u'0', u'0', u'auto',
        u'inactiv  e', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'1', u'stp5_450G_03', u'online', u'18', u'6', u'29.43TB', u'256',
        u'21.68TB', u'8.78TB', u'7.73TB', u'7.75TB', u'29', u'80', u'auto',
        u'i  nactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'4', u'stp5_450G_02', u'online', u'15', u'14', u'24.53TB', u'256',
        u'277.00GB', u'24.26TB', u'24.26TB', u'24.26TB', u'98', u'80',
        u'a  uto', u'inactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'9', u'stp6_450G_03', u'online', u'18', u'6', u'29.43TB', u'256',
        u'21.68TB', u'8.78TB', u'7.73TB', u'7.75TB', u'29', u'80', u'auto',
        u'i  nactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'10', u'stp6_450G_02', u'online', u'15', u'14', u'24.53TB', u'256',
        u'277.00GB', u'24.26TB', u'24.26TB', u'24.26TB', u'98', u'80',
        u'  auto', u'inactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'15', u'stp6_300G_01', u'online', u'15', u'23', u'16.34TB', u'256',
        u'472.50GB', u'15.88TB', u'15.88TB', u'15.88TB', u'97', u'80',
        u'  auto', u'inactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'16', u'stp5_300G_01', u'online', u'15', u'23', u'16.34TB', u'256',
        u'472.50GB', u'15.88TB', u'15.88TB', u'15.88TB', u'97', u'80',
        u'  auto', u'inactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'17', u'Quorum_1', u'online', u'1', u'0', u'512.00MB', u'256',
        u'512.00MB', u'0.00MB', u'0.00MB', u'0.00MB', u'0', u'80', u'auto',
        u'inac  tive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'18', u'Quorum_0', u'online', u'1', u'0', u'512.00MB', u'256',
        u'512.00MB', u'0.00MB', u'0.00MB', u'0.00MB', u'0', u'80', u'auto',
        u'inac  tive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'21', u'stp5_450G_01', u'online', u'12', u'31', u'19.62TB', u'256',
        u'320.00GB', u'19.31TB', u'19.31TB', u'19.31TB', u'98', u'0',
        u'a  uto', u'inactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'22', u'stp6_450G_01', u'online', u'12', u'31', u'19.62TB', u'256',
        u'320.00GB', u'19.31TB', u'19.31TB', u'19.31TB', u'98', u'0',
        u'a  uto', u'inactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'23', u'stp5_600G_01', u'online', u'3', u'2', u'6.54TB', u'256',
        u'512.00MB', u'6.54TB', u'6.54TB', u'6.54TB', u'99', u'80', u'auto',
        u'i  nactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ],
    [
        u'24', u'stp6_600G_01', u'online', u'3', u'2', u'6.54TB', u'256',
        u'512.00MB', u'6.54TB', u'6.54TB', u'6.54TB', u'99', u'80', u'auto',
        u'i  nactive', u'no', u'0.00MB', u'0.00MB', u'0.00MB'
    ]
]

discovery = {
    '': [
        (u'Quorum_0', {}), (u'Quorum_1', {}), (u'Quorum_2', {}),
        (u'stp5_300G_01', {}), (u'stp5_450G_01', {}), (u'stp5_450G_02', {}),
        (u'stp5_450G_03', {}), (u'stp5_600G_01', {}), (u'stp6_300G_01', {}),
        (u'stp6_450G_01', {}), (u'stp6_450G_02', {}), (u'stp6_450G_03', {}),
        (u'stp6_600G_01', {})
    ]
}

checks = {
    '': [
        (
            u'Quorum_0', {
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
                    0, '0% used (0.00 B of 512.00 MB)', [
                        (u'Quorum_0', 0.0, 409.6, 460.8, 0, 512.0),
                        ('fs_size', 512.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 0%', [
                        ('fs_provisioning', 0.0, None, None, 0, 536870912.0)
                    ]
                )
            ]
        ),
        (
            u'Quorum_1', {
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
                    0, '0% used (0.00 B of 512.00 MB)', [
                        (u'Quorum_1', 0.0, 409.6, 460.8, 0, 512.0),
                        ('fs_size', 512.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 0%', [
                        ('fs_provisioning', 0.0, None, None, 0, 536870912.0)
                    ]
                )
            ]
        ),
        (
            u'Quorum_2', {
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
                    0, '0% used (0.00 B of 704.00 MB)', [
                        (u'Quorum_2', 0.0, 563.2, 633.6, 0, 704.0),
                        ('fs_size', 704.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 0%', [
                        ('fs_provisioning', 0.0, None, None, 0, 738197504.0)
                    ]
                )
            ]
        ),
        (
            u'stp5_300G_01', {
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
                    2,
                    '97.18% used (15.88 of 16.34 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp5_300G_01', 16651386.88, 13706985.472000001,
                            15420358.656, 0, 17133731.84
                        ), ('fs_size', 17133731.84, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 97.18%', [
                        (
                            'fs_provisioning', 17460244649082.88, None, None,
                            0, 17966019997859.84
                        )
                    ]
                )
            ]
        ),
        (
            u'stp5_450G_01', {
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
                    2,
                    '98.42% used (19.31 of 19.62 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp5_450G_01', 20248002.56, 16458448.896000002,
                            18515755.008, 0, 20573061.12
                        ), ('fs_size', 20573061.12, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 98.42%', [
                        (
                            'fs_provisioning', 21231569532354.56, None, None,
                            0, 21572418136965.12
                        )
                    ]
                )
            ]
        ),
        (
            u'stp5_450G_02', {
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
                    2,
                    '98.9% used (24.26 of 24.53 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp5_450G_02', 25438453.76, 20577255.424000002,
                            23149412.352, 0, 25721569.28
                        ), ('fs_size', 25721569.28, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 98.9%', [
                        (
                            'fs_provisioning', 26674152089845.76, None, None,
                            0, 26971020229345.28
                        )
                    ]
                )
            ]
        ),
        (
            u'stp5_450G_03', {
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
                    0, '26.33% used (7.75 of 29.43 TB)', [
                        (
                            u'stp5_450G_03', 8126464.0, 24687673.344,
                            27773632.512, 0, 30859591.68
                        ), ('fs_size', 30859591.68, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 29.83%', [
                        (
                            'fs_provisioning', 9653712091873.28, None, None, 0,
                            32358627205447.68
                        )
                    ]
                )
            ]
        ),
        (
            u'stp5_600G_01', {
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
                    2,
                    '100% used (6.54 of 6.54 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp5_600G_01', 6857687.04, 5486149.632,
                            6171918.336, 0, 6857687.04
                        ), ('fs_size', 6857687.04, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 100%', [
                        (
                            'fs_provisioning', 7190806045655.04, None, None, 0,
                            7190806045655.04
                        )
                    ]
                )
            ]
        ),
        (
            u'stp6_300G_01', {
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
                    2,
                    '97.18% used (15.88 of 16.34 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp6_300G_01', 16651386.88, 13706985.472000001,
                            15420358.656, 0, 17133731.84
                        ), ('fs_size', 17133731.84, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 97.18%', [
                        (
                            'fs_provisioning', 17460244649082.88, None, None,
                            0, 17966019997859.84
                        )
                    ]
                )
            ]
        ),
        (
            u'stp6_450G_01', {
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
                    2,
                    '98.42% used (19.31 of 19.62 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp6_450G_01', 20248002.56, 16458448.896000002,
                            18515755.008, 0, 20573061.12
                        ), ('fs_size', 20573061.12, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 98.42%', [
                        (
                            'fs_provisioning', 21231569532354.56, None, None,
                            0, 21572418136965.12
                        )
                    ]
                )
            ]
        ),
        (
            u'stp6_450G_02', {
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
                    2,
                    '98.9% used (24.26 of 24.53 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp6_450G_02', 25438453.76, 20577255.424000002,
                            23149412.352, 0, 25721569.28
                        ), ('fs_size', 25721569.28, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 98.9%', [
                        (
                            'fs_provisioning', 26674152089845.76, None, None,
                            0, 26971020229345.28
                        )
                    ]
                )
            ]
        ),
        (
            u'stp6_450G_03', {
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
                    0, '26.33% used (7.75 of 29.43 TB)', [
                        (
                            u'stp6_450G_03', 8126464.0, 24687673.344,
                            27773632.512, 0, 30859591.68
                        ), ('fs_size', 30859591.68, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 29.83%', [
                        (
                            'fs_provisioning', 9653712091873.28, None, None, 0,
                            32358627205447.68
                        )
                    ]
                )
            ]
        ),
        (
            u'stp6_600G_01', {
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
                    2,
                    '100% used (6.54 of 6.54 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'stp6_600G_01', 6857687.04, 5486149.632,
                            6171918.336, 0, 6857687.04
                        ), ('fs_size', 6857687.04, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 100%', [
                        (
                            'fs_provisioning', 7190806045655.04, None, None, 0,
                            7190806045655.04
                        )
                    ]
                )
            ]
        )
    ]
}
