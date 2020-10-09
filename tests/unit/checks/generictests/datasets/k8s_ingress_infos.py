#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


from cmk.base.discovered_labels import HostLabel

checkname = 'k8s_ingress_infos'

parsed = {
    u'cafe-ingress': {
        u'load_balancers': [{
            u'ip': u'10.0.2.15',
            u'hostname': u''
        }],
        u'backends': [
            [u'cafe.example.com/tea', u'tea-svc', 80],
            [u'cafe.example.com/coffee', u'coffee-svc', 80]
        ],
        u'hosts': {
            u'cafe-secret': [u'cafe.example.com']
        }
    }
}

discovery = {
    '': [
        (u'cafe.example.com/coffee', None), (u'cafe.example.com/tea', None)
    ]
}

checks = {
    '': [
        (
            u'cafe.example.com/coffee', {}, [
                (0, u'Ports: 80, 443', []), (0, u'Service: coffee-svc:80', [])
            ]
        ),
        (
            u'cafe.example.com/tea', {}, [
                (0, u'Ports: 80, 443', []), (0, u'Service: tea-svc:80', [])
            ]
        )
    ]
}
