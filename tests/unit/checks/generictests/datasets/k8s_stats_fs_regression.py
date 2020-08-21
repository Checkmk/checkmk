#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'k8s_stats'

parsed = [
    {
        'filesystem': [
            {
                'available': 96380989440,
                'base_usage': 0,
                'capacity': 103880232960,
                'device': '/dev/vda1',
                'has_inodes': True,
                'inodes': 12902400,
                'inodes_free': 12636910,
                'io_in_progress': 0,
                'io_time': 23038516,
                'read_time': 2320720,
                'reads_completed': 142003,
                'reads_merged': 70,
                'sectors_read': 3784453,
                'sectors_written': 94846416,
                'type': 'vfs',
                'usage': 7482466304,
                'weighted_io_time': 113727436,
                'write_time': 172119032,
                'writes_completed': 4529013,
                'writes_merged': 3894868
            }, {
                'available': 2068180992,
                'base_usage': 0,
                'capacity': 2068193280,
                'device':
                '/var/lib/kubelet/pods/50d6471a-b836-4752-a118-3dcc601e584d/volumes/kubernetes.io~secret/kube-proxy-token-6spq2',
                'has_inodes': True,
                'inodes': 504930,
                'inodes_free': 504921,
                'io_in_progress': 0,
                'io_time': 0,
                'read_time': 0,
                'reads_completed': 0,
                'reads_merged': 0,
                'sectors_read': 0,
                'sectors_written': 0,
                'type': 'vfs',
                'usage': 12288,
                'weighted_io_time': 0,
                'write_time': 0,
                'writes_completed': 0,
                'writes_merged': 0
            }, {
                'available': 0,
                'base_usage': 0,
                'capacity': 0,
                'device': 'overlay_0-97',
                'has_inodes': False,
                'inodes': 0,
                'inodes_free': 0,
                'io_in_progress': 0,
                'io_time': 0,
                'read_time': 0,
                'reads_completed': 0,
                'reads_merged': 0,
                'sectors_read': 0,
                'sectors_written': 0,
                'type': '',
                'usage': 0,
                'weighted_io_time': 0,
                'write_time': 0,
                'writes_completed': 0,
                'writes_merged': 0
            }, {
                'available': 0,
                'base_usage': 0,
                'capacity': 0,
                'device': '/run/user/1000',
                'has_inodes': False,
                'inodes': 0,
                'inodes_free': 0,
                'io_in_progress': 0,
                'io_time': 0,
                'read_time': 0,
                'reads_completed': 0,
                'reads_merged': 0,
                'sectors_read': 0,
                'sectors_written': 0,
                'type': '',
                'usage': 0,
                'weighted_io_time': 0,
                'write_time': 0,
                'writes_completed': 0,
                'writes_merged': 0
            }, {
                'available': 2068193280,
                'base_usage': 0,
                'capacity': 2068193280,
                'device': '/dev/shm',
                'has_inodes': True,
                'inodes': 504930,
                'inodes_free': 504929,
                'io_in_progress': 0,
                'io_time': 0,
                'read_time': 0,
                'reads_completed': 0,
                'reads_merged': 0,
                'sectors_read': 0,
                'sectors_written': 0,
                'type': 'vfs',
                'usage': 0,
                'weighted_io_time': 0,
                'write_time': 0,
                'writes_completed': 0,
                'writes_merged': 0
            }
        ]
    }, None
]

discovery = {
    '': [],
    'network': [],
    'fs': [
        ('/dev/vda1', {}), ('/run/user/1000', {}),
        (
            '/var/lib/kubelet/pods/50d6471a-b836-4752-a118-3dcc601e584d/volumes/kubernetes.io~secret/kube-proxy-token-6spq2',
            {}
        )
    ]
}

checks = {
    'fs': [
        (
            '/dev/vda1', {
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
                    0, '7.22% used (6.98 of 96.75 GB)', [
                        (
                            'fs_used', 7151.8359375, 79254.328125,
                            89161.119140625, 0, 99067.91015625
                        ), ('fs_size', 99067.91015625, None, None, None, None),
                        (
                            'fs_used_percent', 7.219124665313034, None, None,
                            None, None
                        ),
                        (
                            'inodes_used', 265490, 11612160.0, 12257280.0, 0.0,
                            12902400.0
                        )
                    ]
                )
            ]
        ),
        (
            '/run/user/1000', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [(1, 'Size of filesystem is 0 MB', [])]
        ),
        (
            '/var/lib/kubelet/pods/50d6471a-b836-4752-a118-3dcc601e584d/volumes/kubernetes.io~secret/kube-proxy-token-6spq2',
            {
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
                    0, '0.0006% used (12.00 kB of 1.93 GB)', [
                        (
                            'fs_used', 0.01171875, 1577.90625, 1775.14453125,
                            0, 1972.3828125
                        ), ('fs_size', 1972.3828125, None, None, None, None),
                        (
                            'fs_used_percent', 0.0005941417622244668, None,
                            None, None, None
                        ),
                        ('inodes_used', 9, 454437.0, 479683.5, 0.0, 504930.0)
                    ]
                )
            ]
        )
    ]
}
