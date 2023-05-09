#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow


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
        (
            # @docker_version_info^@{"PluginVersion": "0.1", "DockerPyVersion": "3.4.1", "ApiVersion": "1.39"}
            {
                "ServerVersion": "18.09.1",
                "IndexServerAddress": "https://index.docker.io/v1/",
                "ID": "GG7L:A5P4:M6AF:RL3A:7KWZ:VMMK:7MCQ:FX37:LG4A:RXV3:Q6YN:WKYG",
                "Containers": 1,
                "ContainersRunning": 1,
                "ContainersPaused": 0,
                "ContainersStopped": 0,
                "Images": 4,
                "Swarm": {
                    "NodeID": "",
                    "NodeAddr": "",
                    "LocalNodeState": "inactive",
                    "ControlAvailable": False,
                    "Error": "",
                    "RemoteManagers": None
                },
            },
            [
                Attributes(path=['software', 'applications', 'docker'],
                           inventory_attributes={
                               'version': '18.09.1',
                               'registry': 'https://index.docker.io/v1/',
                               'swarm_state': 'inactive',
                               'swarm_node_id': ''
                           },
                           status_attributes={
                               'num_containers_total': 1,
                               'num_containers_running': 1,
                               'num_containers_paused': 0,
                               'num_containers_stopped': 0,
                               'num_images': 4
                           })
            ]),
        ({
            "ServerVersion": "20.10.3",
            "IndexServerAddress": "https://index.docker.io/v1/",
            "Swarm": {
                "LocalNodeState": "active",
                "NodeID": "x2my5tv8bqg0yh5jq98gzodr2",
                "RemoteManagers": [{
                    "NodeID": "x2my5tv8bqg0yh5jq98gzodr2",
                    "Addr": "101.102.103.104:2377"
                }],
            },
            "Containers": 7,
            "ContainersRunning": 4,
            "ContainersPaused": 0,
            "ContainersStopped": 3,
            "Images": 7,
            "Labels": ["this_is_a_label_in=etc_docker_daemon_json", "another=label"],
        }, [
            Attributes(path=['software', 'applications', 'docker'],
                       inventory_attributes={
                           'version': '20.10.3',
                           'registry': 'https://index.docker.io/v1/',
                           'swarm_state': 'active',
                           'swarm_node_id': 'x2my5tv8bqg0yh5jq98gzodr2',
                       },
                       status_attributes={
                           'num_containers_total': 7,
                           'num_containers_running': 4,
                           'num_containers_paused': 0,
                           'num_containers_stopped': 3,
                           'num_images': 7
                       }),
            TableRow(path=['software', 'applications', 'docker', 'node_labels'],
                     key_columns={'label': 'this_is_a_label_in=etc_docker_daemon_json'},
                     inventory_columns={},
                     status_columns={}),
            TableRow(path=['software', 'applications', 'docker', 'node_labels'],
                     key_columns={'label': 'another=label'},
                     inventory_columns={},
                     status_columns={}),
            TableRow(path=['software', 'applications', 'docker', 'swarm_manager'],
                     key_columns={
                         'NodeID': 'x2my5tv8bqg0yh5jq98gzodr2',
                         'Addr': '101.102.103.104:2377',
                     },
                     inventory_columns={},
                     status_columns={}),
        ]),
    ])
def test_inv_docker_node_info(parsed, expected):
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName('docker_node_info'))
    assert plugin
    assert list(plugin.inventory_function(parsed)) == expected
