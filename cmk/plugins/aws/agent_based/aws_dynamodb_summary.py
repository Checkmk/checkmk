#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.aws.constants import AWSRegions
from cmk.plugins.aws.lib import GenericAWSSection, parse_aws


def discover_aws_dynamodb_summary(section: GenericAWSSection) -> DiscoveryResult:
    if section:
        yield Service()


def _build_detail_text_from_tables(tables_by_region: Mapping[str, Mapping], region: str) -> str:
    detail_text_lines = [f"{region}:"]
    tables_names_sorted = sorted(tables_by_region[region].keys())
    for table_name in tables_names_sorted:
        table = tables_by_region[region][table_name]
        bytes_size = render.bytes(table["TableSizeBytes"])
        detail_text_lines.append(
            f"{table_name} -- Items: {table['ItemCount']}, Size: {bytes_size}, Status: {table['TableStatus']}"
        )
    return "\n".join(detail_text_lines)


def check_aws_dynamodb_summary(section: GenericAWSSection) -> CheckResult:
    yield Result(state=State.OK, summary=f"Total number of tables: {len(section)}")
    tables_by_region: dict[str, dict] = {}
    aws_regions = dict(AWSRegions)
    for table in section:
        tables_by_region.setdefault(aws_regions[table["Region"]], {})[table["TableName"]] = table
    regions_sorted = sorted(tables_by_region.keys())
    details = []
    for region in regions_sorted:
        yield Result(state=State.OK, summary=f"{region}: {len(tables_by_region[region])}")
        details.append(_build_detail_text_from_tables(tables_by_region, region))

    if len(details) > 0:
        details_text = "\n".join(details)
        yield Result(state=State.OK, notice="...", details=details_text)


agent_section_aws_dynamodb_summary = AgentSection(
    name="aws_dynamodb_summary",
    parse_function=parse_aws,
)

check_plugin_aws_dynamodb_summary = CheckPlugin(
    name="aws_dynamodb_summary",
    service_name="AWS/DynamoDB Summary",
    discovery_function=discover_aws_dynamodb_summary,
    check_function=check_aws_dynamodb_summary,
)
