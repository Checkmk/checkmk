#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Iterable, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable
from cmk.base.plugins.agent_based.utils.k8s import ContainerSpecs, PodContainers, PodInfo


def parse_kube_pod_container_specs(string_table: StringTable) -> ContainerSpecs:
    """Parses `string_table` into a ContainerSpecs isinstance

    >>> parse_kube_pod_container_specs([['{"containers": {"coredns": {"image_pull_policy": "IfNotPresent"}}}']])
    ContainerSpecs(containers={'coredns': ContainerSpec(image_pull_policy='IfNotPresent')})
    """
    return ContainerSpecs(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_pod_container_specs_v1",
    parsed_section_name="kube_pod_container_specs",
    parse_function=parse_kube_pod_container_specs,
)

register.agent_section(
    name="kube_pod_init_container_specs_v1",
    parsed_section_name="kube_pod_init_container_specs",
    parse_function=parse_kube_pod_container_specs,
)


def inventory_kube_pod(
    section_kube_pod_info: Optional[PodInfo],
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_init_containers: Optional[PodContainers],
    section_kube_pod_container_specs: Optional[ContainerSpecs],
    section_kube_pod_init_container_specs: Optional[ContainerSpecs],
) -> InventoryResult:
    if (
        section_kube_pod_info is None
        or section_kube_pod_container_specs is None
        or section_kube_pod_init_container_specs is None
    ):
        return

    yield Attributes(
        path=["software", "applications", "kube", "pod"],
        inventory_attributes={
            "name": section_kube_pod_info.name,
            "namespace": section_kube_pod_info.namespace,
            "dns_policy": section_kube_pod_info.dns_policy,
            "host_ip": section_kube_pod_info.host_ip,
            "host_network": section_kube_pod_info.host_network,
            "node": section_kube_pod_info.node,
            "pod_ip": section_kube_pod_info.pod_ip,
            "qos_class": section_kube_pod_info.qos_class,
        },
    )
    for label in section_kube_pod_info.labels.values():
        yield TableRow(
            path=["software", "applications", "kube", "labels"],
            key_columns={"label_name": label.name},
            inventory_columns={"label_value": label.value},
        )
    yield from _containers_to_table(section_kube_pod_container_specs, section_kube_pod_containers)
    yield from _containers_to_table(
        section_kube_pod_init_container_specs, section_kube_pod_init_containers
    )


def _containers_to_table(
    container_specs: ContainerSpecs, container_statuses: Optional[PodContainers]
) -> Iterable[TableRow]:
    if container_statuses is not None:
        for name, container_spec in container_specs.containers.items():
            container_status = container_statuses.containers[name]
            yield TableRow(
                path=["software", "applications", "kube", "containers"],
                key_columns={"name": name},
                inventory_columns={
                    "image_pull_policy": container_spec.image_pull_policy,
                    "ready": "yes" if container_status.ready else "no",
                    "restart_count": container_status.restart_count,
                    "image": container_status.image,
                    "image_id": container_status.image_id,
                    "container_id": container_status.container_id,
                },
            )
    else:
        for name, container_spec in container_specs.containers.items():
            yield TableRow(
                path=["software", "applications", "kube", "containers"],
                key_columns={"name": name},
                inventory_columns={
                    "image_pull_policy": container_spec.image_pull_policy,
                    "ready": "no",
                },
            )


register.inventory_plugin(
    name="kube_pod",
    sections=[
        "kube_pod_info",
        "kube_pod_containers",
        "kube_pod_init_containers",
        "kube_pod_container_specs",
        "kube_pod_init_container_specs",
    ],
    inventory_function=inventory_kube_pod,
)
