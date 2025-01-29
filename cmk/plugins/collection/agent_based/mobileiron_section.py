#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable
from cmk.plugins.lib.df import BlocksSubsection, DfBlock, InodesSubsection
from cmk.plugins.lib.mobileiron import Section, SourceHostSection


def parse_mobileiron(string_table: StringTable) -> Section:
    json_raw = json.loads(string_table[0][0])
    return Section(
        policy_violation_count=json_raw.get("policyViolationCount"),
        compliance_state=json_raw.get("complianceState"),
        os_build_version=json_raw.get("osBuildVersion"),
        android_security_patch_level=json_raw.get("androidSecurityPatchLevel"),
        platform_version=json_raw.get("platformVersion"),
        client_version=json_raw.get("clientVersion"),
        uptime=json_raw.get("uptime"),
        ip_address=json_raw.get("ipAddress"),
        device_model=json_raw.get("deviceModel"),
        platform_type=json_raw.get("platformType"),
        registration_state=json_raw.get("registrationState"),
        manufacturer=json_raw.get("manufacturer"),
        serial_number=json_raw.get("serialNumber"),
        dm_partition_name=json_raw.get("dmPartitionName"),
    )


def parse_mobileiron_statistics(string_table: StringTable) -> SourceHostSection:
    json_raw = json.loads(string_table[0][0])
    return SourceHostSection(
        total_count=json_raw.get("total_count"),
        non_compliant=json_raw.get("non_compliant"),
    )


def parse_mobileiron_df(string_table: StringTable) -> tuple[BlocksSubsection, InodesSubsection]:
    json_raw = json.loads(string_table[0][0])
    total = json_raw.get("totalCapacity") * 1024
    available = json_raw.get("availableCapacity") * 1024

    return (
        [
            DfBlock(
                device="/root",
                fs_type=None,
                size_mb=total,
                avail_mb=available,
                reserved_mb=0.0,
                mountpoint="/",
                uuid=None,
            ),
        ],
        [],
    )


def host_label_mobileiron(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/os_family:
            This label is set to the operating system as reported by the agent
            as "AgentOS" (such as "windows" or "linux").

    """

    if section.platform_type == "ANDROID":
        yield HostLabel("cmk/os_family", "android")
    elif section.platform_type == "IOS":
        yield HostLabel("cmk/os_family", "ios")


agent_section_mobileiron_section = AgentSection(
    name="mobileiron_section",
    parse_function=parse_mobileiron,
    host_label_function=host_label_mobileiron,
)

agent_section_mobileiron_statistics = AgentSection(
    name="mobileiron_statistics",
    parse_function=parse_mobileiron_statistics,
)

agent_section_mobileiron_df = AgentSection(
    name="mobileiron_df", parse_function=parse_mobileiron_df, parsed_section_name="df"
)
