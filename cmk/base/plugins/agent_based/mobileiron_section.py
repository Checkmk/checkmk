#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.base.plugins.agent_based.utils.df import BlocksSubsection, DfBlock, InodesSubsection
from cmk.base.plugins.agent_based.utils.mobileiron import Section, SourceHostSection

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


def parse_mobileiron(string_table: StringTable) -> Section:
    json_raw = json.loads(string_table[0][0])
    return Section(
        policyViolationCount=json_raw.get("policyViolationCount"),
        complianceState=json_raw.get("complianceState"),
        osBuildVersion=json_raw.get("osBuildVersion"),
        androidSecurityPatchLevel=json_raw.get("androidSecurityPatchLevel"),
        platformVersion=json_raw.get("platformVersion"),
        clientVersion=json_raw.get("clientVersion"),
        uptime=json_raw.get("uptime"),
        ipAddress=json_raw.get("ipAddress"),
        deviceModel=json_raw.get("deviceModel"),
        platformType=json_raw.get("platformType"),
        registrationState=json_raw.get("registrationState"),
        manufacturer=json_raw.get("manufacturer"),
        serialNumber=json_raw.get("serialNumber"),
        dmPartitionName=json_raw.get("dmPartitionName"),
    )


def parse_mobileiron_source_host(string_table: StringTable) -> SourceHostSection:
    json_raw = json.loads(string_table[0][0])
    return SourceHostSection(
        queryTime=json_raw.get("queryTime"),
        total_count=json_raw.get("total_count"),
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


register.agent_section(
    name="mobileiron_section",
    parse_function=parse_mobileiron,
)

register.agent_section(
    name="mobileiron_source_host",
    parse_function=parse_mobileiron_source_host,
)

register.agent_section(
    name="mobileiron_df", parse_function=parse_mobileiron_df, parsed_section_name="df"
)
