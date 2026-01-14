#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.kube.kube_inventory import labels_to_table
from cmk.plugins.kube.schemata.section import ContainerSpecs, PodContainers, PodInfo


def parse_kube_pod_container_specs(string_table: StringTable) -> ContainerSpecs:
    """Parses `string_table` into a ContainerSpecs isinstance

    >>> parse_kube_pod_container_specs([['{"containers": {"coredns": {"image_pull_policy": "IfNotPresent"}}}']])
    ContainerSpecs(containers={'coredns': ContainerSpec(image_pull_policy='IfNotPresent')})
    """
    return ContainerSpecs.model_validate_json(string_table[0][0])


agent_section_kube_pod_container_specs_v1 = AgentSection(
    name="kube_pod_container_specs_v1",
    parsed_section_name="kube_pod_container_specs",
    parse_function=parse_kube_pod_container_specs,
)

agent_section_kube_pod_init_container_specs_v1 = AgentSection(
    name="kube_pod_init_container_specs_v1",
    parsed_section_name="kube_pod_init_container_specs",
    parse_function=parse_kube_pod_container_specs,
)


def inventorize_kube_pod(
    section_kube_pod_info: PodInfo | None,
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_init_containers: PodContainers | None,
    section_kube_pod_container_specs: ContainerSpecs | None,
    section_kube_pod_init_container_specs: ContainerSpecs | None,
) -> InventoryResult:
    if (
        section_kube_pod_info is None
        or section_kube_pod_container_specs is None
        or section_kube_pod_init_container_specs is None
    ):
        return
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "object": "Pod",
            "name": section_kube_pod_info.name,
            "namespace": section_kube_pod_info.namespace,
        },
    )

    yield Attributes(
        path=["software", "applications", "kube", "pod"],
        inventory_attributes={
            "dns_policy": section_kube_pod_info.dns_policy,
            "host_ip": section_kube_pod_info.host_ip,
            "host_network": section_kube_pod_info.host_network,
            "node": section_kube_pod_info.node,
            "pod_ip": section_kube_pod_info.pod_ip,
            "qos_class": section_kube_pod_info.qos_class,
        },
    )
    yield from labels_to_table(section_kube_pod_info.labels)
    yield from _containers_to_table(section_kube_pod_container_specs, section_kube_pod_containers)
    yield from _containers_to_table(
        section_kube_pod_init_container_specs, section_kube_pod_init_containers
    )


def _containers_to_table(
    container_specs: ContainerSpecs, container_statuses: PodContainers | None
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


inventory_plugin_kube_pod = InventoryPlugin(
    name="kube_pod",
    sections=[
        "kube_pod_info",
        "kube_pod_containers",
        "kube_pod_init_containers",
        "kube_pod_container_specs",
        "kube_pod_init_container_specs",
    ],
    inventory_function=inventorize_kube_pod,
)
