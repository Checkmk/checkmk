#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.kube.schemata.section import ClusterInfo


def inventorize_kube_cluster(
    section: ClusterInfo,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "object": "cluster",
            "name": section.name,
        },
    )

    yield Attributes(
        path=["software", "applications", "kube", "cluster"],
        inventory_attributes={
            "version": section.version,
        },
    )


inventory_plugin_kube_cluster = InventoryPlugin(
    name="kube_cluster",
    sections=["kube_cluster_info"],
    inventory_function=inventorize_kube_cluster,
)
