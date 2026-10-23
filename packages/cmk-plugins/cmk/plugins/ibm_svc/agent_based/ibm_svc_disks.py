#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.ibm_svc.lib import parse_ibm_svc_with_header


@dataclass(frozen=True)
class Disk:
    status: str
    use: str
    capacity: str
    enclosure_id: str
    slot_id: str
    tech_type: str


# Agent output:
# <<<ibm_svc_disk:sep(58)>>>
# 0:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:4:1:24::
# 1:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:3:1:23::
# 2:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:2:1:22::
# 3:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:1:1:21::
# 4:online::member:sas_hdd:558.4GB:7:V7BRZ_mdisk08:0:1:20::
# 5:online::member:sas_hdd:558.4GB:8:V7BRZ_mdisk09:4:5:4::
# 6:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:6:1:18::
# 7:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:5:1:17::
# 8:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:4:1:16::
# 9:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:3:1:15::
# 10:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:2:1:14::
# 11:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:1:1:13::
# 12:online::member:sas_hdd:558.4GB:1:V7BRZ_mdisk02:0:1:12::
# 13:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:6:1:10::
# 14:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:7:1:11::
# 15:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:5:1:9::
# 16:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:3:1:7::
# 17:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:4:1:8::
# 18:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:2:1:6::
# 19:online::member:sas_hdd:558.4GB:16:V7BRZ_mdisk19:1:1:5::

# newer versions report an additional column
# 0:online::member:sas_hdd:558.4GB:7:V7RZ_mdisk8:4:1:24:::inactive
# 1:online::member:sas_hdd:558.4GB:7:V7RZ_mdisk8:3:1:23:::inactive

Section = Sequence[Disk]


class _DiskParams(TypedDict):
    failed_spare_ratio: tuple[float, float]
    offline_spare_ratio: tuple[float, float]
    number_of_spare_disks: tuple[int, int]


def parse_ibm_svc_disks(string_table: Sequence[Sequence[str]]) -> Section:
    dflt_header = [
        "id",
        "status",
        "error_sequence_number",
        "use",
        "tech_type",
        "capacity",
        "mdisk_id",
        "mdisk_name",
        "member_id",
        "enclosure_id",
        "slot_id",
        "auto_manage",
        "drive_class_id",
    ]
    parsed: list[Disk] = []
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        parsed.extend(
            Disk(
                status=row["status"],
                use=row["use"],
                capacity=row["capacity"],
                enclosure_id=row["enclosure_id"],
                slot_id=row["slot_id"],
                tech_type=row["tech_type"],
            )
            for row in rows
        )
    return parsed


def discover_ibm_svc_disks(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_ibm_svc_disks(params: _DiskParams, section: Section) -> CheckResult:
    disks: list[dict[str, str | float]] = []
    for data in section:
        status = data.status
        use = data.use
        capacity = data.capacity

        disk: dict[str, str | float] = {}
        disk["identifier"] = (
            f"Enclosure: {data.enclosure_id}, Slot: {data.slot_id}, Type: {data.tech_type}"
        )

        if capacity.endswith("GB"):
            disk["capacity"] = float(capacity[:-2]) * 1024 * 1024 * 1024
        elif capacity.endswith("TB"):
            disk["capacity"] = float(capacity[:-2]) * 1024 * 1024 * 1024 * 1024
        elif capacity.endswith("PB"):
            disk["capacity"] = float(capacity[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024

        # Failure state is from "use" field; "spare" is also a state here
        disk["state"] = use
        if status == "offline" and use != "failed":
            disk["state"] = "offline"

        disk["type"] = ""  # No type available for IBM SVC disks

        disks.append(disk)

    yield from _check_filer_disks(disks, params)


def _check_filer_disks(disks: list[dict[str, str | float]], params: _DiskParams) -> CheckResult:
    disks_in_state: dict[str, list[dict[str, str | float]]] = {
        "prefailed": [],
        "failed": [],
        "offline": [],
        "spare": [],
    }
    total_capacity = 0.0
    for disk in disks:
        total_capacity += float(disk.get("capacity", 0))
        for what, disk_list in disks_in_state.items():
            if disk["state"] == what:
                disk_list.append(disk)

    yield Result(state=State.OK, summary=f"Total raw capacity: {render.disksize(total_capacity)}")
    yield Metric("total_disk_capacity", total_capacity)

    unavail_disks = (
        len(disks_in_state["prefailed"])
        + len(disks_in_state["failed"])
        + len(disks_in_state["offline"])
    )
    yield Result(state=State.OK, summary=f"Total disks: {len(disks) - unavail_disks}")
    yield Metric("total_disks", len(disks))

    spare_disks = len(disks_in_state["spare"])
    yield from check_levels(
        spare_disks,
        label="Spare disks",
        levels_lower=("fixed", params["number_of_spare_disks"]),
        metric_name="spare_disks",
        render_func=str,
    )

    parity_disks = [disk for disk in disks if disk["type"] == "parity"]
    prefailed_parity = [disk for disk in parity_disks if disk["state"] == "prefailed"]
    if parity_disks:
        yield Result(
            state=State.OK,
            summary=f"Parity disks: {len(parity_disks)} ({len(prefailed_parity)} prefailed)",
        )

    yield Result(state=State.OK, summary=f"Failed disks: {unavail_disks}")
    yield Metric("failed_disks", unavail_disks)

    for name, disk_type in [("Data", "data"), ("Parity", "parity")]:
        total_type_disks = [disk for disk in disks if disk["type"] == disk_type]
        prefailed_disks = [disk for disk in total_type_disks if disk["state"] == "prefailed"]
        if total_type_disks:
            info_text = f"{len(total_type_disks)} disks"
            if prefailed_disks:
                info_text += f" ({len(prefailed_disks)} prefailed)"
            yield Result(state=State.OK, summary=info_text)
            info_texts = [str(disk["identifier"]) for disk in prefailed_disks]
            if info_texts:
                yield Result(
                    state=State.OK,
                    summary=f"{name} Disk Details: {' / '.join(info_texts)}",
                )

    for disk_state, ratio_levels in [
        ("failed", params["failed_spare_ratio"]),
        ("offline", params["offline_spare_ratio"]),
    ]:
        info_texts = [str(disk["identifier"]) for disk in disks_in_state[disk_state]]
        if info_texts:
            yield Result(
                state=State.OK,
                summary=f"{disk_state} Disk Details: {' / '.join(info_texts)}",
            )
            ratio = (
                float(len(disks_in_state[disk_state]))
                / (len(disks_in_state[disk_state]) + len(disks_in_state["spare"]))
                * 100
            )
            yield from check_levels(
                ratio,
                label=f"Too many {disk_state} disks",
                levels_upper=("fixed", ratio_levels),
                render_func=render.percent,
                notice_only=True,
            )


agent_section_ibm_svc_disks = AgentSection(
    name="ibm_svc_disks",
    parse_function=parse_ibm_svc_disks,
)


check_plugin_ibm_svc_disks = CheckPlugin(
    name="ibm_svc_disks",
    service_name="Disk Summary",
    discovery_function=discover_ibm_svc_disks,
    check_function=check_ibm_svc_disks,
    check_ruleset_name="netapp_disks",
    check_default_parameters={
        "failed_spare_ratio": (1.0, 50.0),
        "offline_spare_ratio": (1.0, 50.0),
        "number_of_spare_disks": (2, 1),
    },
)
