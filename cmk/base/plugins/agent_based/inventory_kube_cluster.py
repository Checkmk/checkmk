#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.kube import ClusterInfo


def inventory_kube_cluster(
    section: ClusterInfo,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "name": section.name,
        },
    )

    yield Attributes(
        path=["software", "applications", "kube", "cluster"],
        inventory_attributes={
            "version": section.version,
        },
    )


register.inventory_plugin(
    name="kube_cluster",
    sections=["kube_cluster_info"],
    inventory_function=inventory_kube_cluster,
)
