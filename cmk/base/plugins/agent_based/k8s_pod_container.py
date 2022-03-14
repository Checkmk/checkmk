#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import HostLabel, register, TableRow
from .agent_based_api.v1.type_defs import HostLabelGenerator, InventoryResult
from .utils import docker, k8s

Section = Mapping[str, Mapping[str, Any]]

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def host_labels(section: Section) -> HostLabelGenerator:
    if section:
        yield HostLabel("cmk/kubernetes_object", "pod")
        yield HostLabel("cmk/kubernetes", "yes")


register.agent_section(
    name="k8s_pod_container",
    parse_function=k8s.parse_json,
    host_label_function=host_labels,
)


def inventory_k8s_pod_container(section: Section) -> InventoryResult:
    for container_name, container_data in section.items():
        yield TableRow(
            path=["software", "applications", "kubernetes", "pod_container"],
            key_columns={
                "name": container_name,
            },
            inventory_columns={
                "image": container_data["image"],
                "image_pull_policy": container_data["image_pull_policy"],
                "image_id": (
                    docker.get_short_id(container_data["image_id"])
                    if container_data["image_id"]
                    else "No ID"
                ),
            },
            status_columns={
                "ready": "yes" if container_data["ready"] else "no",
                "restart_count": container_data["restart_count"],
                "container_id": (
                    docker.get_short_id(container_data["container_id"])
                    if container_data["container_id"]
                    else "No ID"
                ),
            },
        )


register.inventory_plugin(
    name="k8s_pod_container",
    inventory_function=inventory_k8s_pod_container,
)
