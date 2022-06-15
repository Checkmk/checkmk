#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ibm_svc_mdiskgrp'

info = [
    [
        '0', 'Quorum_2', 'online', '1', '0', '704.00MB', '64', '704.00MB',
        '0.00MB', '0.00MB', '0.00MB', '0', '0', 'auto', 'inactiv  e', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '1', 'stp5_450G_03', 'online', '18', '6', '29.43TB', '256', '21.68TB',
        '8.78TB', '7.73TB', '7.75TB', '29', '80', 'auto', 'i  nactive', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '4', 'stp5_450G_02', 'online', '15', '14', '24.53TB', '256',
        '277.00GB', '24.26TB', '24.26TB', '24.26TB', '98', '80', 'a  uto',
        'inactive', 'no', '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '9', 'stp6_450G_03', 'online', '18', '6', '29.43TB', '256', '21.68TB',
        '8.78TB', '7.73TB', '7.75TB', '29', '80', 'auto', 'i  nactive', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '10', 'stp6_450G_02', 'online', '15', '14', '24.53TB', '256',
        '277.00GB', '24.26TB', '24.26TB', '24.26TB', '98', '80', '  auto',
        'inactive', 'no', '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '15', 'stp6_300G_01', 'online', '15', '23', '16.34TB', '256',
        '472.50GB', '15.88TB', '15.88TB', '15.88TB', '97', '80', '  auto',
        'inactive', 'no', '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '16', 'stp5_300G_01', 'online', '15', '23', '16.34TB', '256',
        '472.50GB', '15.88TB', '15.88TB', '15.88TB', '97', '80', '  auto',
        'inactive', 'no', '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '17', 'Quorum_1', 'online', '1', '0', '512.00MB', '256', '512.00MB',
        '0.00MB', '0.00MB', '0.00MB', '0', '80', 'auto', 'inac  tive', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '18', 'Quorum_0', 'online', '1', '0', '512.00MB', '256', '512.00MB',
        '0.00MB', '0.00MB', '0.00MB', '0', '80', 'auto', 'inac  tive', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '21', 'stp5_450G_01', 'online', '12', '31', '19.62TB', '256',
        '320.00GB', '19.31TB', '19.31TB', '19.31TB', '98', '0', 'a  uto',
        'inactive', 'no', '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '22', 'stp6_450G_01', 'online', '12', '31', '19.62TB', '256',
        '320.00GB', '19.31TB', '19.31TB', '19.31TB', '98', '0', 'a  uto',
        'inactive', 'no', '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '23', 'stp5_600G_01', 'online', '3', '2', '6.54TB', '256', '512.00MB',
        '6.54TB', '6.54TB', '6.54TB', '99', '80', 'auto', 'i  nactive', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ],
    [
        '24', 'stp6_600G_01', 'online', '3', '2', '6.54TB', '256', '512.00MB',
        '6.54TB', '6.54TB', '6.54TB', '99', '80', 'auto', 'i  nactive', 'no',
        '0.00MB', '0.00MB', '0.00MB'
    ]
]

discovery = {
    '': [
        ('Quorum_0', {}), ('Quorum_1', {}), ('Quorum_2', {}),
        ('stp5_300G_01', {}), ('stp5_450G_01', {}), ('stp5_450G_02', {}),
        ('stp5_450G_03', {}), ('stp5_600G_01', {}), ('stp6_300G_01', {}),
        ('stp6_450G_01', {}), ('stp6_450G_02', {}), ('stp6_450G_03', {}),
        ('stp6_600G_01', {})
    ]
}

checks = {
    '': [
        (
            'Quorum_0', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0% used (0 B of 512 MiB)', [
                        ('fs_used', 0.0, 409.6, 460.8, 0, 512.0),
                        ('fs_size', 512.0, None, None, None, None),
                        ('fs_used_percent', 0.0, None, None, None, None)
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
            'Quorum_1', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0% used (0 B of 512 MiB)', [
                        ('fs_used', 0.0, 409.6, 460.8, 0, 512.0),
                        ('fs_size', 512.0, None, None, None, None),
                        ('fs_used_percent', 0.0, None, None, None, None)
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
            'Quorum_2', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0% used (0 B of 704 MiB)', [
                        ('fs_used', 0.0, 563.2, 633.6, 0, 704.0),
                        ('fs_size', 704.0, None, None, None, None),
                        ('fs_used_percent', 0.0, None, None, None, None)
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
            'stp5_300G_01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '97.18% used (15.9 of 16.3 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 16651386.88, 13706985.472000001,
                            15420358.656, 0, 17133731.84
                        ), ('fs_size', 17133731.84, None, None, None, None),
                        (
                            'fs_used_percent', 97.18482252141983, None, None,
                            None, None
                        )
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
            'stp5_450G_01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '98.42% used (19.3 of 19.6 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 20248002.56, 16458448.896000002,
                            18515755.008, 0, 20573061.12
                        ), ('fs_size', 20573061.12, None, None, None, None),
                        (
                            'fs_used_percent', 98.41997961264015, None, None,
                            None, None
                        )
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
            'stp5_450G_02', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '98.90% used (24.3 of 24.5 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 25438453.76, 20577255.424000002,
                            23149412.352, 0, 25721569.28
                        ), ('fs_size', 25721569.28, None, None, None, None),
                        (
                            'fs_used_percent', 98.89930697105585, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Provisioning: 98.90%', [
                        (
                            'fs_provisioning', 26674152089845.76, None, None,
                            0, 26971020229345.28
                        )
                    ]
                )
            ]
        ),
        (
            'stp5_450G_03', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '26.33% used (7.75 of 29.4 TiB)', [
                        (
                            'fs_used', 8126464.0, 24687673.344, 27773632.512,
                            0, 30859591.68
                        ), ('fs_size', 30859591.68, None, None, None, None),
                        (
                            'fs_used_percent', 26.33367312266395, None, None,
                            None, None
                        )
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
            'stp5_600G_01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '100.00% used (6.54 of 6.54 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 6857687.04, 5486149.632, 6171918.336, 0,
                            6857687.04
                        ), ('fs_size', 6857687.04, None, None, None, None),
                        ('fs_used_percent', 100.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 100.00%', [
                        (
                            'fs_provisioning', 7190806045655.04, None, None, 0,
                            7190806045655.04
                        )
                    ]
                )
            ]
        ),
        (
            'stp6_300G_01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '97.18% used (15.9 of 16.3 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 16651386.88, 13706985.472000001,
                            15420358.656, 0, 17133731.84
                        ), ('fs_size', 17133731.84, None, None, None, None),
                        (
                            'fs_used_percent', 97.18482252141983, None, None,
                            None, None
                        )
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
            'stp6_450G_01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '98.42% used (19.3 of 19.6 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 20248002.56, 16458448.896000002,
                            18515755.008, 0, 20573061.12
                        ), ('fs_size', 20573061.12, None, None, None, None),
                        (
                            'fs_used_percent', 98.41997961264015, None, None,
                            None, None
                        )
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
            'stp6_450G_02', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '98.90% used (24.3 of 24.5 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 25438453.76, 20577255.424000002,
                            23149412.352, 0, 25721569.28
                        ), ('fs_size', 25721569.28, None, None, None, None),
                        (
                            'fs_used_percent', 98.89930697105585, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Provisioning: 98.90%', [
                        (
                            'fs_provisioning', 26674152089845.76, None, None,
                            0, 26971020229345.28
                        )
                    ]
                )
            ]
        ),
        (
            'stp6_450G_03', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '26.33% used (7.75 of 29.4 TiB)', [
                        (
                            'fs_used', 8126464.0, 24687673.344, 27773632.512,
                            0, 30859591.68
                        ), ('fs_size', 30859591.68, None, None, None, None),
                        (
                            'fs_used_percent', 26.33367312266395, None, None,
                            None, None
                        )
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
            'stp6_600G_01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    2,
                    '100.00% used (6.54 of 6.54 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'fs_used', 6857687.04, 5486149.632, 6171918.336, 0,
                            6857687.04
                        ), ('fs_size', 6857687.04, None, None, None, None),
                        ('fs_used_percent', 100.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Provisioning: 100.00%', [
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
