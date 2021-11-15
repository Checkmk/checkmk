#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import zip_longest
from typing import Dict

from .agent_based_api.v1 import Attributes, HostLabel, register, TableRow
from .agent_based_api.v1.type_defs import HostLabelGenerator, InventoryResult, StringTable
from .utils import docker

Section = Dict


def parse_docker_node_info(string_table: StringTable) -> Section:
    loaded: Section = {}
    # docker_node_info section may be present multiple times,
    # this is how the docker agent plugin reports errors.
    # Key 'Unknown' is present if there is a python exception
    # key 'Critical' is present if the python docker lib is not found
    string_table_iter = iter(string_table)
    for local_string_table in zip_longest(string_table_iter, string_table_iter):
        # local_string_table holds two consecutive elements of string_table.
        # first loop: [string_table[0], string_table[1]]
        # second loop: [string_table[1], string_table[2]]
        # etc
        parsed = docker.parse(local_string_table).data
        loaded.update(parsed)
    return loaded


def host_labels_docker_node_info(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/docker_object:node :
            This Label is set, if the corresponding host is a docker node.

    """
    if section:
        yield HostLabel("cmk/docker_object", "node")


register.agent_section(
    name="docker_node_info",
    parse_function=parse_docker_node_info,
    host_label_function=host_labels_docker_node_info,
)


def inventory_docker_node_info(section: Section) -> InventoryResult:
    if not section:
        return

    docker_path = ["software", "applications", "docker"]
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
            path=docker_path,
            inventory_attributes=inventory_attributes,
            status_attributes=status_inventory,
        )

    if swarm_data and (swarm_managers := swarm_data.get("RemoteManagers")):
        swarm_manager_path = ["software", "applications", "docker", "swarm_manager"]
        for swarm_manager in swarm_managers:
            if "NodeID" in swarm_manager:
                yield TableRow(
                    path=swarm_manager_path,
                    key_columns={"NodeID": swarm_manager["NodeID"]},
                    inventory_columns={k: v for k, v in swarm_manager.items() if k != "NodeID"},
                    status_columns={},
                )

    labels_path = ["software", "applications", "docker", "node_labels"]
    for label in section.get("Labels", []):
        yield TableRow(
            path=labels_path,
            key_columns={
                "label": label,
            },
            inventory_columns={},
            status_columns={},
        )


register.inventory_plugin(
    name="docker_node_info",
    inventory_function=inventory_docker_node_info,
)
