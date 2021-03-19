#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.docker_node_info import parse_docker_node_info

checkname = 'docker_node_info'


parsed = parse_docker_node_info([
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.39"}'],
    ['{"Name": "klappson"}'],
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.39"}'],
    ['{"Unknown": "Plugin exception in section_node_disk_usage: Kokosnuss geklaut"}'],
])


discovery = {
    '': [(None, {})],
    'containers': [(None, {})],
}


checks = {
    '': [
        (None, {}, [
            (0, u'Daemon running on host klappson', []),
            (3, u'Plugin exception in section_node_disk_usage: Kokosnuss geklaut', []),
        ]),
    ],
}
