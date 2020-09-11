#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.discovered_labels import HostLabel

DEPRECATION_WARNING = (1, (
    "Deprecated plugin/agent (see long output)(!)\nYou are using legacy code, which may lead to "
    "crashes and/or incomplete information. Please upgrade the monitored host to use the plugin "
    "'mk_docker.py'."
), [])

checkname = 'docker_node_info'


info = [['']]


discovery = {'': [(None, {}), HostLabel(u'cmk/docker_object', u'node')],
            'containers': [(None, {})]}


checks = {
    '': [
        (None, {}, [DEPRECATION_WARNING]),
    ],
    'containers': [
        (None, {}, [
            (3, 'Containers: count not present in agent output', []),
            (3, 'Running: count not present in agent output', []),
            (3, 'Paused: count not present in agent output', []),
            (3, 'Stopped: count not present in agent output', []),
            DEPRECATION_WARNING,
        ]),
    ],
}
