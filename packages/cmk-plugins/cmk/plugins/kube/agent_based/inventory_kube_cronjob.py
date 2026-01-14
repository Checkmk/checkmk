#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.kube.schemata.section import CronJobInfo


def inventorize_kube_cronjob(
    section: CronJobInfo,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "object": "CronJob",
            "name": section.name,
            "namespace": section.namespace,
        },
    )


inventory_plugin_kube_cronjob = InventoryPlugin(
    name="kube_cronjob",
    sections=["kube_cronjob_info"],
    inventory_function=inventorize_kube_cronjob,
)
