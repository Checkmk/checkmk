#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils import docker

Section = Dict[str, str]


def parse_docker_container_labels(string_table: StringTable) -> Section:
    return docker.parse(string_table).data


register.agent_section(
    name="docker_container_labels",
    parse_function=parse_docker_container_labels,
)


def inventory_docker_container_labels(section: Section) -> InventoryResult:
    yield Attributes(
        path=docker.INVENTORY_BASE_PATH + ["container"],
        inventory_attributes={"labels": docker.format_labels(section)},
    )


register.inventory_plugin(
    name="docker_container_labels",
    inventory_function=inventory_docker_container_labels,
)
