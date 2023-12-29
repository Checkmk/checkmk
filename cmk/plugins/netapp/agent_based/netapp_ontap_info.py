#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import Attributes, CheckPlugin, InventoryPlugin, Result, Service, State
from cmk.agent_based.v2.type_defs import CheckResult, DiscoveryResult, InventoryResult
from cmk.plugins.netapp import models

Section = Mapping[str, models.NodeModel]

# <<<netapp_api_node:sep(0)>>>
# {
#     "controller": {"cpu": {"count": 36, "processor": "Intel(R) Xeon(R) CPU E5-2697 v4 @ 2.30GHz"}},
#     "model": "AFF-A700",
#     "name": "mcc_darz_a-02",
#     "nvram": {"battery_state": "battery_ok"},
#     "serial_number": "211709000156",
#     "system_id": "0537063878",
#     "uuid": "1e13de87-bda2-11ed-b8bd-00a098c50e5b",
#     "version": {
#         "full": "NetApp Release 9.12.1P6: Fri Aug 04 00:26:53 UTC 2023",
#         "generation": 9,
#         "major": 12,
#         "minor": 1,
#     },
# }
# {
#     "controller": {"cpu": {"count": 36, "processor": "Intel(R) Xeon(R) CPU E5-2697 v4 @ 2.30GHz"}},
#     "model": "AFF-A700",
#     "name": "mcc_darz_a-01",
#     "nvram": {"battery_state": "battery_ok"},
#     "serial_number": "211709000155",
#     "system_id": "0537063936",
#     "uuid": "8f2677e2-bda7-11ed-88df-00a098c54c0b",
#     "version": {
#         "full": "NetApp Release 9.12.1P6: Fri Aug 04 00:26:53 UTC 2023",
#         "generation": 9,
#         "major": 12,
#         "minor": 1,
#     },
# }


def discovery_netapp_ontap_info(section: Section) -> DiscoveryResult:
    yield Service()


def check_netapp_ontap_info(section: Section) -> CheckResult:
    values = list(section.values())
    if not values:
        return
    yield Result(state=State.OK, summary=f"Version: {values[0].version.full}")


check_plugin_netapp_ontap_info = CheckPlugin(
    name="netapp_ontap_info",
    service_name="NetApp Version",
    sections=["netapp_ontap_node"],
    discovery_function=discovery_netapp_ontap_info,
    check_function=check_netapp_ontap_info,
)


def inventory_netapp_ontap_info(section: Section) -> InventoryResult:
    nodes = list(section.values())
    if not nodes:
        return
    hw_system = {
        "model": nodes[0].model,
        "product": nodes[0].system_machine_type,
        "serial": nodes[0].serial_number,
        "id": nodes[0].system_id,
    }
    hw_cpu = {
        "cores": nodes[0].cpu_count,
        "model": nodes[0].cpu_processor,
    }

    yield Attributes(path=["hardware", "cpu"], inventory_attributes=hw_cpu)
    yield Attributes(path=["hardware", "system"], inventory_attributes=hw_system)


inventory_plugin_netapp_ontap_info = InventoryPlugin(
    name="netapp_ontap_info",
    sections=["netapp_ontap_node"],
    inventory_function=inventory_netapp_ontap_info,
)
