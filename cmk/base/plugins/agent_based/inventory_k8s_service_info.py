#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pydantic

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable


class ServiceInfo(pydantic.BaseModel):
    cluster_ip: str
    load_balance_ip: str


def parse_k8s_service_info(string_table: StringTable) -> ServiceInfo:
    return ServiceInfo.parse_raw(string_table[0][0])


register.agent_section(
    name="k8s_service_info",
    parse_function=parse_k8s_service_info,
)


def inventory_kube_service_info(section: ServiceInfo) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "kubernetes", "service_info"],
        inventory_attributes={
            "cluster_ip": section.cluster_ip,
            "load_balance_ip": section.load_balance_ip,
        },
    )


register.inventory_plugin(
    name="k8s_service_info",
    inventory_function=inventory_kube_service_info,
)
