#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'proxmox_node_subscription'

info = [
    [
        u'{"checktime": "1580263801", "key": "pve1c-ad47525c4c", "level": "c", "nextduedate": "2020-02-19", "productname": "Proxmox VE Community Subscription 1 CPU/year", "regdate": "2018-12-11 00:00:00", "serverid": "AB69F7C91742EDBFFB3529BFC6293BE7", "sockets": 1, "status": "Active", "url": "https://www.proxmox.com/proxmox-ve/pricing", "validdirectory": "AB69F7C91742EDBFFB3529BFC6293BE7"}'
    ]
]

discovery = {'': [(None, {})]}

checks = {'': [(None, {}, [(0, u'Status: active', [])])]}
