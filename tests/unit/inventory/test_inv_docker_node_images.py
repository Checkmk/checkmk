#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest


class MockTree(object):
    def __init__(self):
        self.data = {}

    def get_dict(self, path):
        return self.data.setdefault(path, dict())

    def get_list(self, path):
        return self.data.setdefault(path, list())


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


def call_plugin(parsed):
    inventory_tree = MockTree()
    status_data_tree = MockTree()

    context = {'inv_info': {}}
    execfile(os.path.join(os.path.dirname(__file__), '../../../checks/docker.include'), context)
    execfile(os.path.join(os.path.dirname(__file__), '../../../inventory/docker_node_images'),
             context)
    function = context["inv_docker_node_images"]
    function(parsed, inventory_tree, status_data_tree)
    return inventory_tree.data, status_data_tree.data


def test_inv_docker_node_images():
    parsed = [
        line.split("\0") if "\0" in line else line.split(" ") for line in AGENT_OUTPUT.split("\n")
    ]
    assert call_plugin(parsed) == ({
        'software.applications.docker.images:': [{
            'repotags': u'hello:world',
            'repodigests': '',
            'creation': u'2021-02-12T11:29:33.063968737Z',
            'size': 1231733,
            'id': u'b2bf42ca5d8f',
            'labels': u'image_label_command_line: 1, image_label_dockerfile: 2'
        }],
    }, {
        'software.applications.docker.containers:': [{
            'id': u'891a6f6a1c28',
            'image': u'b2bf42ca5d8f',
            'name': u'/relaxed_shaw',
            'creation': u'2021-02-12T12:15:28.230110819Z',
            'labels': u'another_container_label: 2, container: label, image_label_command_line: 1, image_label_dockerfile: 2',
            'status': u'running'
        }],
        'software.applications.docker.images:': [{
            'id': u'b2bf42ca5d8f',
            'amount_containers': 1,
        }]
    })
