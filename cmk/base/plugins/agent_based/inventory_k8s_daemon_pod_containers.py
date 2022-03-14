#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Mapping

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Mapping]

########################################################################
# NOTE: This inv plugin (and associated special agent) is deprecated and
#       will be removed in Checkmk version 2.2.
########################################################################


def parse_k8s_daemon_pod_containers(string_table: StringTable) -> Section:
    try:
        return json.loads(string_table[0][0])
    except IndexError:
        return {}


register.agent_section(
    name="k8s_daemon_pod_containers",
    parse_function=parse_k8s_daemon_pod_containers,
)


def inventory_k8s_daemon_pod_containers(section: Section) -> InventoryResult:
    path = ["software", "applications", "kubernetes", "daemon_pod_containers"]
    for container_name, container_data in sorted(section.items()):
        yield TableRow(
            path=path,
            key_columns={
                "name": container_name,
            },
            inventory_columns={
                "image": container_data["image"],
                "image_pull_policy": container_data["image_pull_policy"],
            },
            status_columns={},
        )


register.inventory_plugin(
    name="k8s_daemon_pod_containers",
    inventory_function=inventory_k8s_daemon_pod_containers,
)
