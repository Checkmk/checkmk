#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)
from cmk.plugins.lib import docker

Section = dict[str, str]


def parse_docker_container_labels(string_table: StringTable) -> Section:
    return docker.parse(string_table).data


agent_section_docker_container_labels = AgentSection(
    name="docker_container_labels",
    parse_function=parse_docker_container_labels,
)


def inventory_docker_container_labels(section: Section) -> InventoryResult:
    yield Attributes(
        path=docker.INVENTORY_BASE_PATH + ["container"],
        inventory_attributes={"labels": docker.format_labels(section)},
    )


inventory_plugin_docker_container_labels = InventoryPlugin(
    name="docker_container_labels",
    inventory_function=inventory_docker_container_labels,
)
