#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.kube import CronJobInfo


def inventory_kube_cronjob(
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


register.inventory_plugin(
    name="kube_cronjob",
    sections=["kube_cronjob_info"],
    inventory_function=inventory_kube_cronjob,
)
