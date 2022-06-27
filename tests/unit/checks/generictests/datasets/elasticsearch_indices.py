#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'elasticsearch_indices'

info = [
    [u'.monitoring-kibana-6', u'971.0', u'765236.0'],
    [u'filebeat', u'28298.0', u'21524354.0'],
    [u'.monitoring-es-6', u'11986.0', u'15581765.0']
]

discovery = {
    '': [
        (u'.monitoring-es-6', {}), (u'.monitoring-kibana-6', {}),
        (u'filebeat', {})
    ]
}

checks = {
    '': [
        (
            u'.monitoring-es-6', {}, [
                (
                    0, 'Total count: 11986 docs',
                    [('elasticsearch_count', 11986.0, None, None, None, None)]
                ),
                (
                    0, 'Average count: 0 docs per Minute', [
                        (
                            'elasticsearch_count_rate', 0.0, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Total size: 14.9 MiB', [
                        (
                            'elasticsearch_size', 15581765.0, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Average size: 0 B  per Minute',
                    [('elasticsearch_size_rate', 0.0, None, None, None, None)]
                )
            ]
        ),
        (
            u'.monitoring-kibana-6', {}, [
                (
                    0, 'Total count: 971 docs', [
                        ('elasticsearch_count', 971.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Average count: 0 docs per Minute', [
                        (
                            'elasticsearch_count_rate', 0.0, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Total size: 747 KiB',
                    [('elasticsearch_size', 765236.0, None, None, None, None)]
                ),
                (
                    0, 'Average size: 0 B  per Minute',
                    [('elasticsearch_size_rate', 0.0, None, None, None, None)]
                )
            ]
        ),
        (
            u'filebeat', {}, [
                (
                    0, 'Total count: 28298 docs',
                    [('elasticsearch_count', 28298.0, None, None, None, None)]
                ),
                (
                    0, 'Average count: 0 docs per Minute', [
                        (
                            'elasticsearch_count_rate', 0.0, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Total size: 20.5 MiB', [
                        (
                            'elasticsearch_size', 21524354.0, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Average size: 0 B  per Minute',
                    [('elasticsearch_size_rate', 0.0, None, None, None, None)]
                )
            ]
        )
    ]
}
