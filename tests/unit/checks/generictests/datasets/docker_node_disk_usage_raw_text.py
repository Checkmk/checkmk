#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

DEPRECATION_WARNING = (1, (
    "Deprecated plugin/agent (see long output)(!)\nYou are using legacy code, which may lead to "
    "crashes and/or incomplete information. Please upgrade the monitored host to use the plugin "
    "'mk_docker.py'."
), [])


checkname = 'docker_node_disk_usage'

info = [
    ['TYPE                TOTAL               ACTIVE              SIZE                RECLAIMABLE'],
    [
        'Images              15                  2                   9.57GB              8.674GB (90%)'
    ],
    [
        'Containers          2                   1                   1.226GB             1.224GB (99%)'
    ],
    ['Local Volumes       1                   1                   9.323MB             0B (0%)'],
    ['Build Cache         0                   0                   0B                  0B'],
]

discovery = {'': [('build cache', {}), ('containers', {}), ('images', {}), ('local volumes', {})]}

checks = {
    '': [
        ('build cache', {}, [
            (0, 'Size: 0.00 B', [('size', 0, None, None, None, None)]),
            (0, 'Reclaimable: 0.00 B', [('reclaimable', 0, None, None, None, None)]),
            (0, 'Count: 0', [('count', 0, None, None, None, None)]),
            (0, 'Active: 0', [('active', 0, None, None, None, None)]),
            DEPRECATION_WARNING,
        ]),
        ('containers', {}, [
            (0, 'Size: 1.14 GB', [('size', 1226000000, None, None, None, None)]),
            (0, 'Reclaimable: 1.14 GB', [('reclaimable', 1224000000, None, None, None, None)]),
            (0, 'Count: 2', [('count', 2, None, None, None, None)]),
            (0, 'Active: 1', [('active', 1, None, None, None, None)]),
            DEPRECATION_WARNING,
        ]),
        ('images', {}, [
            (0, 'Size: 8.91 GB', [('size', 9570000000, None, None, None, None)]),
            (0, 'Reclaimable: 8.08 GB', [('reclaimable', 8674000000, None, None, None, None)]),
            (0, 'Count: 15', [('count', 15, None, None, None, None)]),
            (0, 'Active: 2', [('active', 2, None, None, None, None)]),
            DEPRECATION_WARNING,
        ]),
        ('local volumes', {}, [
            (0, 'Size: 8.89 MB', [('size', 9323000, None, None, None, None)]),
            (0, 'Reclaimable: 0.00 B', [('reclaimable', 0, None, None, None, None)]),
            (0, 'Count: 1', [('count', 1, None, None, None, None)]),
            (0, 'Active: 1', [('active', 1, None, None, None, None)]),
            DEPRECATION_WARNING,
        ]),
    ],
}
