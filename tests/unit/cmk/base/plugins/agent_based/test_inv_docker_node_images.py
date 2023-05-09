#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow

AGENT_OUTPUT = (
    '@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}\n'
    '[[[images]]]\n'
    '{"RepoDigests": [], "Id": "sha256:b2bf42ca5d8f3245e58832a1d67d5ce9cfbfe754e9b552b5e5f0e6d26dea4aa5", '
    '"RepoTags": ["hello:world"], "Created": "2021-02-12T11:29:33.063968737Z", "VirtualSize": 1231733, '
    '"Config": {"Labels": {"image_label_command_line": "1", "image_label_dockerfile": "2"}}}\n'
    '[[[containers]]]\n'
    '{"Id": "891a6f6a1c2807c544b0342d79fa79da05cc7f8d40927d72fe7b2513622b91d1", "Created": '
    '"2021-02-12T12:15:28.230110819Z", "Name": "/relaxed_shaw", "State": {"Status": "running", '
    '"Running": true, "Paused": false, "Restarting": false, "OOMKilled": false, "Dead": false, '
    '"Pid": 3436979, "ExitCode": 0, "Error": "", "StartedAt": "2021-02-12T12:15:28.592056523Z", '
    '"FinishedAt": "0001-01-01T00:00:00Z"}, "Config": {"Labels": {"another_container_label": "2", '
    '"container": "label", "image_label_command_line": "1", "image_label_dockerfile": "2"}}, '
    '"Image": "sha256:b2bf42ca5d8f3245e58832a1d67d5ce9cfbfe754e9b552b5e5f0e6d26dea4aa5"}')


@pytest.mark.usefixtures("config_load_all_inventory_plugins")
def test_inv_docker_node_images():
    parsed = [
        line.split("\0") if "\0" in line else line.split(" ") for line in AGENT_OUTPUT.split("\n")
    ]
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName('docker_node_images'))
    assert plugin
    assert list(plugin.inventory_function(parsed)) == [
        TableRow(
            path=['software', 'applications', 'docker', 'containers'],
            key_columns={
                'id': '891a6f6a1c28',
                'image': 'b2bf42ca5d8f',
                'name': '/relaxed_shaw',
                'creation': '2021-02-12T12:15:28.230110819Z',
                'labels': 'another_container_label: 2, container: label, image_label_command_line: 1, image_label_dockerfile: 2',
                'status': 'running'
            },
            inventory_columns={},
            status_columns={}),
        TableRow(path=['software', 'applications', 'docker', 'images'],
                 key_columns={'id': 'b2bf42ca5d8f'},
                 inventory_columns={
                     'repotags': 'hello:world',
                     'repodigests': '',
                     'creation': '2021-02-12T11:29:33.063968737Z',
                     'size': 1231733,
                     'labels': 'image_label_command_line: 1, image_label_dockerfile: 2'
                 },
                 status_columns={}),
        TableRow(path=['software', 'applications', 'docker', 'images'],
                 key_columns={'id': 'b2bf42ca5d8f'},
                 inventory_columns={},
                 status_columns={'amount_containers': 1}),
    ]
