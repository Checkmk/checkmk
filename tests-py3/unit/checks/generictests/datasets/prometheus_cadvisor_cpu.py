#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'cadvisor_cpu'

info = [
    [
        u'{"cpu_user": [{"value": "0.10996819381471273", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}], "cpu_system": [{"value": "0.12688637747851422", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}]}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'User: 0.11%', [
                        ('user', 0.10996819381471273, None, None, None, None)
                    ]
                ),
                (
                    0, 'System: 0.13%',
                    [('system', 0.12688637747851422, None, None, None, None)]
                ),
                (
                    0, 'Total CPU: 0.24%', [
                        ('util', 0.23685457129322696, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
