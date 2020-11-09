#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.mark.usefixtures("config_load_all_inventory_plugins")
@pytest.mark.parametrize(
    'parsed, expected',
    [
        ({
            "nothing": "usable"
        }, [
            Attributes(path=["software", "applications", "docker"]),
        ]),
        (
            {
                'ServerVersion': u'1.17',
                'IndexServerAddress': u'https://registry.access.redhat.com/v1/',
                u'Containers': 11,
                u'ContainersPaused': 0,
                u'ContainersRunning': 11,
                u'ContainersStopped': 0,
                u'Images': 22,
                u'Swarm': {
                    'LocalNodeState': u'active',
                    'NodeID': u'Hier koennte ihre Werbung stehen.'
                },
            },
            [
                Attributes(path=["software", "applications", "docker"])._replace(
                    inventory_attributes={
                        "version": "1.17",
                        "registry": u'https://registry.access.redhat.com/v1/',
                        "swarm_state": "active",
                        "swarm_node_id": u'Hier koennte ihre Werbung stehen.',
                    },
                    status_attributes={
                        "num_containers_total": 11,  # type: ignore[dict-item]
                        "num_containers_running": 11,  # type: ignore[dict-item]
                        "num_containers_paused": 0,  # type: ignore[dict-item]
                        "num_containers_stopped": 0,  # type: ignore[dict-item]
                        "num_images": 22,  # type: ignore[dict-item]
                    },
                ),
            ]),
    ])
def test_inv_docker_node_info(parsed, expected):
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName('docker_node_info'))
    assert plugin
    assert list(plugin.inventory_function(parsed)) == expected
