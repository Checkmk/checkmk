#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'docker_container_mem'

info = [
    [
        '@docker_version_info',
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'
    ],
    [
        '{"usage": 4034560, "limit": 16690180096, "stats": {"unevictable": 0, "total_inactive_file": 0, "total_rss_huge": 0, "hierarchical_memsw_limit": 0, "total_cache": 0, "total_mapped_file": 0, "mapped_file": 0, "pgfault": 41101, "total_writeback": 0, "hierarchical_memory_limit": 9223372036854771712, "total_active_file": 0, "rss_huge": 0, "cache": 0, "active_anon": 860160, "pgmajfault": 0, "total_pgpgout": 29090, "writeback": 0, "pgpgout": 29090, "total_active_anon": 860160, "total_unevictable": 0, "total_pgfault": 41101, "total_pgmajfault": 0, "total_inactive_anon": 0, "inactive_file": 0, "pgpgin": 29300, "total_dirty": 0, "total_pgpgin": 29300, "rss": 860160, "active_file": 0, "inactive_anon": 0, "dirty": 0, "total_rss": 860160}, "max_usage": 7208960}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'levels': (150.0, 200.0)
            }, [
                (
                    0, 'RAM: 0.02% - 3.85 MB of 15.54 GB', [
                        ('mem_used', 4034560, None, None, 0, 16690180096),
                        (
                            'mem_used_percent', 0.02417325623087153, None,
                            None, 0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 4034560, 25035270144.0,
                            33380360192.0, 0, 16690180096
                        )
                    ]
                )
            ]
        )
    ]
}
