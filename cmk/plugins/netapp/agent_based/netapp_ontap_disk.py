#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    render,
    Service,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.filerdisks import (
    check_filer_disks,
    FILER_DISKS_CHECK_DEFAULT_PARAMETERS,
    FilerDisk,
)
from cmk.plugins.netapp import models

Section = Sequence[models.DiskModel]

# <<<netapp_ontap_disk:sep(0)>>>
# {
#     "container_type": "mediator",
#     "model": "PHA-DISK",
#     "serial_number": "3436343536316534",
#     "uid": "34363435:36316534:00000000:00000000:00000000:00000000:00000000:00000000:00000000:00000000",
#     "vendor": "NETAPP",
# }
# {
#     "container_type": "mediator",
#     "model": "PHA-DISK",
#     "serial_number": "3535653766393933",
#     "uid": "35356537:66393933:00000000:00000000:00000000:00000000:00000000:00000000:00000000:00000000",
#     "vendor": "NETAPP",
# }


def parse_netapp_ontap_disk(string_table: StringTable) -> Section:
    return [models.DiskModel.model_validate_json(line[0]) for line in string_table]


agent_section_netapp_ontap_disk = AgentSection(
    name="netapp_ontap_disk",
    parse_function=parse_netapp_ontap_disk,
)


def inventory_netapp_ontap_disk(section: Section) -> InventoryResult:
    for disk in sorted(section, key=lambda disk: disk.uid):
        yield TableRow(
            path=["hardware", "storage", "disks"],
            key_columns={
                "signature": disk.uid,
            },
            inventory_columns={
                "serial": disk.serial_number,
                "vendor": disk.vendor,
                "bay": disk.bay,
            },
            status_columns={},
        )


inventory_plugin_netapp_ontap_disk = InventoryPlugin(
    name="netapp_ontap_disk", inventory_function=inventory_netapp_ontap_disk
)


def discovery_netapp_ontap_disk_summary(section: Section) -> DiscoveryResult:
    yield Service()


def check_netapp_ontap_disk_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    Unlike the old netapp api with the new api "physical-space" and "disk-type" are missing.
    Cfr the old plug-in to see where they were used.
    """

    if "broken_spare_ratio" in params:
        params = {"failed_spare_ratio": params["broken_spare_ratio"]}

    check_filer_section: list[FilerDisk] = [
        FilerDisk(
            state={"broken": "failed", "spare": "spare"}.get(disk_model.container_type, "ok"),
            identifier=f"Serial: {disk_model.serial_number}, Size: {render.bytes(disk_model.space())}",
            capacity=disk_model.space(),
        )
        for disk_model in section
        if disk_model.container_type not in ["remote", "partner"]
    ]

    yield from check_filer_disks(
        check_filer_section,
        params,
    )


check_plugin_netapp_ontap_disk_summary = CheckPlugin(
    name="netapp_ontap_disk_summary",
    service_name="NetApp Disks Summary",
    sections=["netapp_ontap_disk"],
    discovery_function=discovery_netapp_ontap_disk_summary,
    check_function=check_netapp_ontap_disk_summary,
    check_ruleset_name="netapp_disks",
    check_default_parameters=FILER_DISKS_CHECK_DEFAULT_PARAMETERS,
)
