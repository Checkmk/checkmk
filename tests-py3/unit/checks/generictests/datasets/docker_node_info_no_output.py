#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.discovered_labels import HostLabel

checkname = 'docker_node_info'


info = [['']]


discovery = {'': [(None, {}), HostLabel(u'cmk/docker_object', u'node')],
            'containers': [(None, {})]}


checks = {'': [(None, {}, [])],
          'containers': [(None,
                          {},
                          [(3, 'Containers: count not present in agent output', []),
                           (3, 'Running: count not present in agent output', []),
                           (3, 'Paused: count not present in agent output', []),
                           (3, 'Stopped: count not present in agent output', [])])]}
