#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'docker_container_mem'

info = [
    ['cache', '41316352'], ['rss', '79687680'], ['rss_huge', '8388608'],
    ['mapped_file', '5976064'], ['swap', '0'], ['pgpgin', '7294455'],
    ['pgpgout', '7267468'], ['pgfault', '39514980'], ['pgmajfault', '111'],
    ['inactive_anon', '0'], ['active_anon', '79642624'],
    ['inactive_file', '28147712'], ['active_file', '13168640'],
    ['unevictable', '0'], ['hierarchical_memory_limit', '9223372036854771712'],
    ['hierarchical_memsw_limit', '9223372036854771712'],
    ['total_cache', '41316352'], ['total_rss', '79687680'],
    ['total_rss_huge', '8388608'], ['total_mapped_file', '5976064'],
    ['total_swap', '0'], ['total_pgpgin', '7294455'],
    ['total_pgpgout', '7267468'], ['total_pgfault', '39514980'],
    ['total_pgmajfault', '111'], ['total_inactive_anon', '0'],
    ['total_active_anon', '79642624'], ['total_inactive_file', '28147712'],
    ['total_active_file', '13168640'], ['total_unevictable', '0'],
    ['usage_in_bytes', '121810944'], ['limit_in_bytes', '9223372036854771712'],
    ['MemTotal:', '65660592', 'kB']
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'levels': (150.0, 200.0)
            }, [
                (
                    0, 'RAM: 0.06% - 37.36 MB of 62.62 GB', [
                        ('mem_used', 39178240, None, None, 0, 67236446208),
                        (
                            'mem_used_percent', 0.05826934974939001, None,
                            None, 0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 39178240, 100854669312.0,
                            134472892416.0, 0, 67236446208
                        )
                    ]
                )
            ]
        )
    ]
}
