#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = "proxmox_node_info"

info = [
    [
        '{'
        ' "status": "online",'
        ' "proxmox_version": {'
        '    "release": "6.1",'
        '    "repoid": "806edfe1",'
        '    "version": "6.1-8"'
        ' },'
        ' "lxc": ["103", "104", "101", "108"],'
        ' "qemu": ["102", "106", "105", "100", "107"],'
        ' "subscription": {'
        '    "status": "Active",'
        '    "checktime": "1586914751",'
        '    "key": "pve1c-ad47525c4c",'
        '    "level": "c",'
        '    "nextduedate": "2021-02-19",'
        '    "productname": "Proxmox VE Community Subscription 1 CPU/year", '
        '    "regdate": "2018-12-11 00:00:00"'
        ' }'
        '}'
    ]
]

discovery = {'': [(None, None)]}

checks = {
    '': [
        (
            None, {
                'check_status': None,
                'subscription': None
            }, [
                (0, "Status: 'online'", []), (0, "Subscription: 'Active'", []),
                (0, "Version: '6.1-8'", []),
                (0, "Hosted VMs: 4 * 'lxc', 5 * 'qemu'", [])
            ]
        ),
        (
            None, {
                'required_node_status': None,
                'required_subscription_status': None
            }, [
                (0, "Status: 'online'", []), (0, "Subscription: 'Active'", []),
                (0, "Version: '6.1-8'", []),
                (0, "Hosted VMs: 4 * 'lxc', 5 * 'qemu'", [])
            ]
        )
    ]
}
