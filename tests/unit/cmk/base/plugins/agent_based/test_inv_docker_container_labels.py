#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

AGENT_OUTPUT = (
    '@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}\n'
    '{"com.docker.swarm.node.id": "x2my5tv8bqg0yh5jq98gzodr2", '
    '"com.docker.swarm.service.id": "nrgxet23d204ywz1rjl8fbtff", '
    '"com.docker.swarm.service.name": "redis", '
    '"com.docker.swarm.task": "", '
    '"com.docker.swarm.task.id": "jjp7380fb51n4figvv4zxl350", '
    '"com.docker.swarm.task.name": "redis.1.jjp7380fb51n4figvv4zxl350"}')


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_inv_docker_container_labels():
    info = [
        line.split("\0") if "\0" in line else line.split(" ") for line in AGENT_OUTPUT.split("\n")
    ]
    plugin = agent_based_register.get_inventory_plugin(
        InventoryPluginName('docker_container_labels'))
    assert plugin
    assert list(plugin.inventory_function(info)) == [
        Attributes(path=['software', 'applications', 'docker', 'container'],
                   inventory_attributes={
                       'labels': ('com.docker.swarm.node.id: x2my5tv8bqg0yh5jq98gzodr2, '
                                  'com.docker.swarm.service.id: nrgxet23d204ywz1rjl8fbtff, '
                                  'com.docker.swarm.service.name: redis, '
                                  'com.docker.swarm.task: , '
                                  'com.docker.swarm.task.id: jjp7380fb51n4figvv4zxl350, '
                                  'com.docker.swarm.task.name: redis.1.jjp7380fb51n4figvv4zxl350')
                   },
                   status_attributes={})
    ]
