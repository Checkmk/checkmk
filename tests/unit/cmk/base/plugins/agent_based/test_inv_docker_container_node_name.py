#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.utils.docker import AgentOutputMalformatted

from .utils_inventory import sort_inventory_result

AGENT_OUTPUT = """@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}
{"NodeName": "klappben"}"""


def test_inv_docker_container_node_name(fix_register):
    info = [line.split("\0") for line in AGENT_OUTPUT.split("\n")]
    plugin = fix_register.inventory_plugins[InventoryPluginName("docker_container_node_name")]
    assert sort_inventory_result(plugin.inventory_function(info)) == sort_inventory_result(
        [
            Attributes(
                path=["software", "applications", "docker", "container"],
                inventory_attributes={"node_name": "klappben"},
                status_attributes={},
            )
        ]
    )


def test_inv_docker_container_node_name_legacy_agent_output(fix_register):
    plugin = fix_register.inventory_plugins[InventoryPluginName("docker_container_node_name")]
    with pytest.raises(AgentOutputMalformatted):
        list(plugin.inventory_function([["node_name"]]))
