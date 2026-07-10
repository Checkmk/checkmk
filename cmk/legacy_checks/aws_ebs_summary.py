#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import parse_aws


@dataclass(frozen=True)
class EbsStatusDetail:
    name: str
    status: str


@dataclass(frozen=True)
class EbsVolumeStatus:
    status: str
    details: Sequence[EbsStatusDetail]


@dataclass(frozen=True)
class EbsSummaryVolume:
    volume_id: str
    volume_type: str
    state: str
    encrypted: bool | None = None
    create_time: str | None = None
    volume_status: EbsVolumeStatus | None = None


AWSEBSStorageTypes = {
    "standard": "Magnetic volumes",
    "gp2": "General Purpose SSD (gp2)",
    "gp3": "General Purpose SSD (gp3)",
    "io1": "Provisioned IOPS SSD (io1)",
    "io2": "Provisioned IOPS SSD (io2)",
    "st1": "Throughput Optimized HDD",
    "sc1": "Cold HDD",
}


def parse_aws_summary(string_table: StringTable) -> Mapping[str, EbsSummaryVolume]:
    parsed: dict[str, EbsSummaryVolume] = {}
    for row in parse_aws(string_table):
        if (vid := row["VolumeId"]) in parsed:
            continue
        volume_status = None
        if (raw_status := row.get("VolumeStatus")) is not None:
            volume_status = EbsVolumeStatus(
                status=raw_status["Status"],
                details=[
                    EbsStatusDetail(name=detail["Name"], status=detail["Status"])
                    for detail in raw_status.get("Details", [])
                ],
            )
        parsed[vid] = EbsSummaryVolume(
            volume_id=vid,
            volume_type=row["VolumeType"],
            state=row["State"],
            encrypted=row.get("Encrypted"),
            create_time=row.get("CreateTime"),
            volume_status=volume_status,
        )
    return parsed


def discover_aws_ebs_summary(section: Mapping[str, EbsSummaryVolume]) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_ebs_summary(section: Mapping[str, EbsSummaryVolume]) -> CheckResult:
    stores_by_state: dict[str, list[str]] = {}
    stores_by_type: dict[str, list[str]] = {}
    long_output = []
    for volume_id, row in section.items():
        stores_by_state.setdefault(row.state, []).append(volume_id)
        stores_by_type.setdefault(row.volume_type, []).append(volume_id)
        long_output.append(
            f"Volume: {volume_id}, Status: {row.state}, Type: {row.volume_type}, "
            f"Encrypted: {row.encrypted}, Creation time: {row.create_time}"
        )

    yield Result(state=State.OK, summary=f"Stores: {len(section)}")
    for state, stores in stores_by_state.items():
        yield Result(state=State.OK, summary=f"{state}: {len(stores)}")
    for type_, stores in stores_by_type.items():
        yield Result(
            state=State.OK,
            summary=f"{AWSEBSStorageTypes.get(type_, f'unknown[{type_}]')}: {len(stores)}",
        )
    if long_output:
        yield Result(state=State.OK, notice="\n".join(long_output))


agent_section_aws_ebs_summary = AgentSection(
    name="aws_ebs_summary",
    parse_function=parse_aws_summary,
)


check_plugin_aws_ebs_summary = CheckPlugin(
    name="aws_ebs_summary",
    service_name="AWS/EBS Summary",
    discovery_function=discover_aws_ebs_summary,
    check_function=check_aws_ebs_summary,
)


def discover_aws_ebs_summary_health(section: Mapping[str, EbsSummaryVolume]) -> DiscoveryResult:
    for volume_id, volume in section.items():
        if volume.volume_status is not None:
            yield Service(item=volume_id)


def check_aws_ebs_summary_health(item: str, section: Mapping[str, EbsSummaryVolume]) -> CheckResult:
    if (ebs_data := section.get(item)) is None:
        return
    if (volume_status := ebs_data.volume_status) is None:
        return
    ebs_status = volume_status.status
    yield Result(
        state=State.OK if ebs_status.lower() == "ok" else State.CRIT,
        summary=f"Status: {ebs_status}",
    )
    for detail in volume_status.details:
        yield Result(state=State.OK, summary=f"{detail.name}: {detail.status}")


check_plugin_aws_ebs_summary_health = CheckPlugin(
    name="aws_ebs_summary_health",
    service_name="AWS/EBS Health %s",
    sections=["aws_ebs_summary"],
    discovery_function=discover_aws_ebs_summary_health,
    check_function=check_aws_ebs_summary_health,
)
