#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils import docker

Section = Mapping[str, object]


def parse_docker_container_node_name(string_table: StringTable) -> Section:
    return docker.parse(string_table).data


register.agent_section(
    name="inventory_docker_container_node_name",
    parse_function=parse_docker_container_node_name,
)


def inventory_docker_container_node_name(section: Section) -> InventoryResult:

    if (node := section.get("NodeName")) is not None:
        yield Attributes(
            path=["software", "applications", "docker", "container"],
            inventory_attributes={"node_name": str(node)},
        )


register.inventory_plugin(
    name="inventory_docker_container_node_name",
    inventory_function=inventory_docker_container_node_name,
)
