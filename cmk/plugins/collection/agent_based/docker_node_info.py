#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import zip_longest

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.lib import docker


def parse_docker_node_info(string_table: StringTable) -> docker.NodeInfoSection:
    loaded: dict = {}
    # docker_node_info section may be present multiple times,
    # this is how the docker agent plug-in reports errors.
    # Key 'Unknown' is present if there is a python exception
    # key 'Critical' is present if the python docker lib is not found
    string_table_iter = iter(string_table)
    for version_info, payload in zip_longest(string_table_iter, string_table_iter, fillvalue=None):
        # local_string_table holds two consecutive elements of string_table.
        # first loop: (string_table[0], string_table[1])
        # second loop: (string_table[2], string_table[3])
        # etc
        if version_info is None or payload is None:
            raise Exception(
                "docker_node_info has wrong number of string_table elements. "
                "This is an internal error and should never happen."
            )
        for key, val in docker.parse([version_info, payload]).data.items():
            if key in ("Unknown", "Critical"):
                loaded.setdefault(key, []).append(val)
            else:
                loaded[key] = val
    return loaded


def host_labels_docker_node_info(section: docker.NodeInfoSection) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/docker_object:node :
            This Label is set, if the corresponding host is a docker node.

    """
    if section:
        yield HostLabel("cmk/docker_object", "node")


agent_section_docker_node_info = AgentSection(
    name="docker_node_info",
    parse_function=parse_docker_node_info,
    host_label_function=host_labels_docker_node_info,
)


def inventory_docker_node_info(section: docker.NodeInfoSection) -> InventoryResult:
    if not section:
        return

    swarm_data = section.get("Swarm")

    inventory_attributes = {
        ikey: section[skey]
        for ikey, skey in [("version", "ServerVersion"), ("registry", "IndexServerAddress")]
        if skey in section
    }
    if swarm_data:
        # {"NodeID":"","NodeAddr":"","LocalNodeState":"inactive","ControlAvailable":false,"Error":"","RemoteManagers":null}
        inventory_attributes.update(
            {
                ikey: swarm_data[skey]
                for ikey, skey in [("swarm_state", "LocalNodeState"), ("swarm_node_id", "NodeID")]
                if skey in swarm_data
            }
        )
    status_inventory = {
        ikey: section[skey]
        for ikey, skey in [
            ("num_containers_total", "Containers"),
            ("num_containers_running", "ContainersRunning"),
            ("num_containers_paused", "ContainersPaused"),
            ("num_containers_stopped", "ContainersStopped"),
            ("num_images", "Images"),
        ]
        if skey in section
    }
    if inventory_attributes or status_inventory:
        yield Attributes(
            path=["software", "applications", "docker"],
            inventory_attributes=inventory_attributes,
            status_attributes=status_inventory,
        )

    if swarm_data and (swarm_managers := swarm_data.get("RemoteManagers")):
        for swarm_manager in swarm_managers:
            if "NodeID" in swarm_manager:
                yield TableRow(
                    path=["software", "applications", "docker", "swarm_manager"],
                    key_columns={"NodeID": swarm_manager["NodeID"]},
                    inventory_columns={k: v for k, v in swarm_manager.items() if k != "NodeID"},
                    status_columns={},
                )

    # Some outputs may look like: {"Labels": null}
    for label in section.get("Labels", []) or []:
        yield TableRow(
            path=["software", "applications", "docker", "node_labels"],
            key_columns={
                "label": label,
            },
            inventory_columns={},
            status_columns={},
        )


inventory_plugin_docker_node_info = InventoryPlugin(
    name="docker_node_info",
    inventory_function=inventory_docker_node_info,
)
