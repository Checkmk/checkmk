#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult

from .lib import SectionPodmanContainerInspect


def inventory_podman_container(
    section: SectionPodmanContainerInspect,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "podman", "container"],
        inventory_attributes={
            "hostname": section.config.hostname,
            "pod": section.pod,
            "labels": ",".join(f"{k}={v}" for k, v in section.config.labels.items()),
        },
    )

    yield Attributes(
        path=["software", "applications", "podman", "network"],
        inventory_attributes={
            "ip_address": section.network.ip_address,
            "gateway": section.network.gateway,
            "mac_address": section.network.mac_address,
        },
    )


inventory_plugin_podman_container = InventoryPlugin(
    name="inventory_podman_container",
    sections=["podman_container_inspect"],
    inventory_function=inventory_podman_container,
)
