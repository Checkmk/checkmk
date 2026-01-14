#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
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


def inventorize_netapp_ontap_disk(section: Section) -> InventoryResult:
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
    name="netapp_ontap_disk",
    inventory_function=inventorize_netapp_ontap_disk,
)


def discovery_netapp_ontap_disk_summary(section: Section) -> DiscoveryResult:
    yield Service()


@dataclass(frozen=True, kw_only=True)
class FilerDisk:
    state: str
    identifier: str
    type: str = ""
    capacity: int = 0


FILER_DISKS_CHECK_DEFAULT_PARAMETERS = {
    "failed_spare_ratio": (1.0, 50.0),
    "offline_spare_ratio": (1.0, 50.0),
}


def _check_total_capacity(disks: Sequence[FilerDisk]) -> CheckResult:
    total_capacity = sum(disk.capacity for disk in disks)

    if not total_capacity:
        return

    yield Result(state=State.OK, summary=f"Total raw capacity: {render.disksize(total_capacity)}")
    yield Metric("disk_capacity", total_capacity)


def _check_spare_disks(spare_disks: int, spare_disk_levels: Any) -> CheckResult:
    yield from check_levels(
        value=int(spare_disks),
        levels_lower=(
            ("fixed", (float(spare_disk_levels[0]), float(spare_disk_levels[1])))
            if spare_disk_levels
            else ("no_levels", None)
        ),
        label="Spare disks",
        metric_name="spare_disks",
        render_func=lambda x: f"{int(x)}",
    )


def _check_parity_disks(disks: Sequence[FilerDisk]) -> CheckResult:
    parity_disks = [disk for disk in disks if disk.type == "parity"]
    prefailed_parity = [disk for disk in parity_disks if disk.state == "prefailed"]
    if len(parity_disks) > 0:
        yield Result(
            state=State.OK,
            summary=f"Parity disks: {len(parity_disks)} ({len(prefailed_parity)} prefailed)",
        )

    for name, disk_type in [("Data", "data"), ("Parity", "parity")]:
        total_disks = [disk for disk in disks if disk.type == disk_type]
        prefailed_disks = [disk for disk in total_disks if disk.state == "prefailed"]
        if len(total_disks) > 0:
            info_text = "%s disks" % len(total_disks)
            if len(prefailed_disks) > 0:
                info_text += f" ({len(prefailed_disks)} prefailed)"
            yield Result(state=State.OK, summary=info_text)

            info_texts = []
            for disk in prefailed_disks:
                info_texts.append(disk.identifier)
            if len(info_texts) > 0:
                yield Result(
                    state=State.OK,
                    summary=f"{name} Disk Details: {' / '.join(info_texts)}",
                )


def _check_failed_offline_disks(
    state: Mapping[str, Sequence[FilerDisk]], params: Mapping[str, Any]
) -> CheckResult:
    for disk_state in ["failed", "offline"]:
        info_texts = []
        for disk in state[disk_state]:
            info_texts.append(disk.identifier)
        if len(info_texts) > 0:
            yield Result(
                state=State.OK,
                summary="{} Disk Details: {}".format(disk_state, " / ".join(info_texts)),
            )

            warn, crit = params["%s_spare_ratio" % disk_state]
            ratio = (
                float(len(state[disk_state])) / (len(state[disk_state]) + len(state["spare"])) * 100
            )
            return_state = None
            if ratio >= crit:
                return_state = State.CRIT
            elif ratio >= warn:
                return_state = State.WARN
            if return_state is not None:
                yield Result(
                    state=return_state,
                    summary=f"Too many {disk_state} disks (warn/crit at {warn:.1f}%/{crit:.1f}%)",
                )


def check_filer_disks(disks: Sequence[FilerDisk], params: Mapping[str, Any]) -> CheckResult:
    """
    We consider prefailed disk unavailable.
    In the code here, this assumption has been made for 9 years without any problem ever being raised.
    """

    yield from _check_total_capacity(disks)

    state: dict[str, list[FilerDisk]] = {
        "prefailed": [],
        "failed": [],
        "offline": [],
        "spare": [],
    }

    for disk in disks:
        for what, disks_in_state in state.items():
            if disk.state == what:
                disks_in_state.append(disk)

    unavail_disks = len(state["prefailed"] + state["failed"] + state["offline"])
    yield Result(state=State.OK, summary=f"Total disks: {len(disks) - unavail_disks}")
    yield Metric("disks", len(disks))

    yield from _check_spare_disks(len(state["spare"]), params.get("number_of_spare_disks"))

    yield Result(state=State.OK, summary=f"Failed disks: {unavail_disks}")
    yield Metric(name="failed_disks", value=unavail_disks)

    yield from _check_parity_disks(disks)

    yield from _check_failed_offline_disks(state, params)


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
