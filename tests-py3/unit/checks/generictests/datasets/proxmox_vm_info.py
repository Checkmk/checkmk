#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'proxmox_vm_info'

info = [
    [
        '{"name": "aq-test.lan.mathias-kettner.de",'
        ' "node": "pve-dc4-001",'
        ' "status": "running",'
        ' "type": "qemu",'
        ' "vmid": "133"}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (0, "VM ID: 133", []), (0, "Status: running", []),
                (0, "Type: qemu", []), (0, "Host: pve-dc4-001", [])
            ]
        ),
        (
            None, {
                'required_vm_status': None
            }, [
                (0, "VM ID: 133", []), (0, "Status: running", []),
                (0, "Type: qemu", []), (0, "Host: pve-dc4-001", [])
            ]
        ),
        (
            None, {
                'required_vm_status': 'walking'
            }, [
                (0, "VM ID: 133", []), (1, "Status: running (required: walking)", []),
                (0, "Type: qemu", []), (0, "Host: pve-dc4-001", [])
            ]
        ),
    ]
}
