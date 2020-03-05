#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


from cmk.base.discovered_labels import HostLabel

checkname = 'k8s_stateful_set_replicas'

parsed = {u'ready_replicas': 2, u'replicas': 2, u'strategy_type': 'RollingUpdate'}

discovery = {'': [
    (None, {}), HostLabel(u'cmk/kubernetes_object', u'statefulset')
]}

checks = {'': [
    (None, {}, [
        (0, 'Ready: 2/2', [
            ('ready_replicas', 2, None, None, None, None),
            ('total_replicas', 2, None, None, None, None)
        ]),
        (0, 'Strategy: RollingUpdate', [])],
    )
]}
