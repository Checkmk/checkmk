#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Attributes, StringTable
from cmk.plugins.collection.agent_based.inventory_docker_container_node_name import (
    agent_section_docker_container_node_name,
    inventory_docker_container_node_name,
    inventory_plugin_docker_container_node_name,
    parse_docker_container_node_name,
    Section,
)
from cmk.plugins.lib.docker import AgentOutputMalformatted, MultipleNodesMarker

AGENT_OUTPUT = """@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}
{"NodeName": "klappben"}"""


def _string_table(agent_output: str) -> StringTable:
    return [line.split("\0") for line in agent_output.split("\n")]


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    return parse_docker_container_node_name(_string_table(AGENT_OUTPUT))


def test_inv_docker_container_node_name(section: Section) -> None:
    assert list(inventory_docker_container_node_name(section)) == [
        Attributes(
            path=["software", "applications", "docker", "container"],
            inventory_attributes={"node_name": "klappben"},
            status_attributes={},
        )
    ]


def test_inv_docker_container_node_name_multiple_nodes() -> None:
    section = parse_docker_container_node_name(_string_table(AGENT_OUTPUT + "\n" + AGENT_OUTPUT))
    assert isinstance(section, MultipleNodesMarker)
    assert not list(inventory_docker_container_node_name(section))


def test_inv_docker_container_node_name_legacy_agent_output() -> None:
    with pytest.raises(AgentOutputMalformatted):
        parse_docker_container_node_name([["node_name"]])


def test_inv_docker_container_node_name_consumes_the_section_of_the_agent_plugin() -> None:
    # mk_docker.py writes the piggyback section "docker_container_node_name".
    assert agent_section_docker_container_node_name.name == "docker_container_node_name"
    assert inventory_plugin_docker_container_node_name.name == "docker_container_node_name"
