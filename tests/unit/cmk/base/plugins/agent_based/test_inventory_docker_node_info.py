#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.docker_node_info import inventory_docker_node_info

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "parsed, expected",
    [
        (
            {"nothing": "usable"},
            [],
        ),
        (
            {
                "ServerVersion": "1.17",
                "IndexServerAddress": "https://registry.access.redhat.com/v1/",
                "Containers": 11,
                "ContainersPaused": 0,
                "ContainersRunning": 11,
                "ContainersStopped": 0,
                "Images": 22,
                "Swarm": {
                    "LocalNodeState": "active",
                    "NodeID": "Hier koennte ihre Werbung stehen.",
                },
            },
            [
                Attributes(path=["software", "applications", "docker"])._replace(
                    inventory_attributes={
                        "version": "1.17",
                        "registry": "https://registry.access.redhat.com/v1/",
                        "swarm_state": "active",
                        "swarm_node_id": "Hier koennte ihre Werbung stehen.",
                    },
                    status_attributes={
                        "num_containers_total": 11,
                        "num_containers_running": 11,
                        "num_containers_paused": 0,
                        "num_containers_stopped": 0,
                        "num_images": 22,
                    },
                ),
            ],
        ),
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
                    "RemoteManagers": None,
                },
            },
            [
                Attributes(
                    path=["software", "applications", "docker"],
                    inventory_attributes={
                        "version": "18.09.1",
                        "registry": "https://index.docker.io/v1/",
                        "swarm_state": "inactive",
                        "swarm_node_id": "",
                    },
                    status_attributes={
                        "num_containers_total": 1,
                        "num_containers_running": 1,
                        "num_containers_paused": 0,
                        "num_containers_stopped": 0,
                        "num_images": 4,
                    },
                )
            ],
        ),
        (
            {
                "ServerVersion": "20.10.3",
                "IndexServerAddress": "https://index.docker.io/v1/",
                "Swarm": {
                    "LocalNodeState": "active",
                    "NodeID": "x2my5tv8bqg0yh5jq98gzodr2",
                    "RemoteManagers": [
                        {"NodeID": "x2my5tv8bqg0yh5jq98gzodr2", "Addr": "101.102.103.104:2377"}
                    ],
                },
                "Containers": 7,
                "ContainersRunning": 4,
                "ContainersPaused": 0,
                "ContainersStopped": 3,
                "Images": 7,
                "Labels": ["this_is_a_label_in=etc_docker_daemon_json", "another=label"],
            },
            [
                Attributes(
                    path=["software", "applications", "docker"],
                    inventory_attributes={
                        "version": "20.10.3",
                        "registry": "https://index.docker.io/v1/",
                        "swarm_state": "active",
                        "swarm_node_id": "x2my5tv8bqg0yh5jq98gzodr2",
                    },
                    status_attributes={
                        "num_containers_total": 7,
                        "num_containers_running": 4,
                        "num_containers_paused": 0,
                        "num_containers_stopped": 3,
                        "num_images": 7,
                    },
                ),
                TableRow(
                    path=["software", "applications", "docker", "swarm_manager"],
                    key_columns={
                        "NodeID": "x2my5tv8bqg0yh5jq98gzodr2",
                    },
                    inventory_columns={
                        "Addr": "101.102.103.104:2377",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "docker", "node_labels"],
                    key_columns={"label": "this_is_a_label_in=etc_docker_daemon_json"},
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "docker", "node_labels"],
                    key_columns={"label": "another=label"},
                    inventory_columns={},
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inv_docker_node_info(fix_register, parsed, expected) -> None:
    assert sort_inventory_result(inventory_docker_node_info(parsed)) == sort_inventory_result(
        expected
    )
