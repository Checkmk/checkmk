#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    TableRow,
)
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
    yield from (Service(item=node_name) for node_name in section)


def check_netapp_ontap_info(item: str, section: Section) -> CheckResult:
    if (node_info := section.get(item)) is None:
        return
    yield Result(state=State.OK, summary=f"Version: {node_info.version.full}")


check_plugin_netapp_ontap_info = CheckPlugin(
    name="netapp_ontap_info",
    service_name="NetApp Version %s",
    sections=["netapp_ontap_node"],
    discovery_function=discovery_netapp_ontap_info,
    check_function=check_netapp_ontap_info,
)


def inventorize_netapp_ontap_info(section: Section) -> InventoryResult:
    for node in section.values():
        hw_system = {
            "model": node.model,
            "product": node.system_machine_type,
            "serial": node.serial_number,
            "id": node.system_id,
        }
        hw_cpu = {
            "cores": node.cpu_count,
            "model": node.cpu_processor,
        }

        yield TableRow(
            path=["hardware", "cpu", "nodes"],
            key_columns={
                "node_name": node.name,
            },
            inventory_columns=hw_cpu,
            status_columns={},
        )

        yield TableRow(
            path=["hardware", "system", "nodes"],
            key_columns={
                "node_name": node.name,
            },
            inventory_columns=hw_system,
            status_columns={},
        )


inventory_plugin_netapp_ontap_info = InventoryPlugin(
    name="netapp_ontap_info",
    sections=["netapp_ontap_node"],
    inventory_function=inventorize_netapp_ontap_info,
)
