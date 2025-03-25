#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.base.check_legacy_includes.aws import AWSRegions

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.aws.lib import GenericAWSSection, parse_aws

check_info = {}


def discover_aws_dynamodb_summary(section: GenericAWSSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_dynamodb_summary(item, params, parsed):
    tables_by_region: dict[str, dict] = {}

    for table in parsed:
        tables_by_region.setdefault(AWSRegions[table["Region"]], {})[table["TableName"]] = table

    regions_sorted = sorted(tables_by_region.keys())
    long_output = []

    yield 0, "Total number of tables: %s" % len(parsed)

    for region in regions_sorted:
        tables_region = tables_by_region[region]
        yield 0, f"{region}: {len(tables_region)}"

        tables_names_sorted = sorted(tables_region.keys())
        long_output.append("%s:" % region)

        for table_name in tables_names_sorted:
            table = tables_region[table_name]
            long_output.append(
                "%s -- Items: %s, Size: %s, Status: %s"
                % (
                    table_name,
                    table["ItemCount"],
                    render.bytes(table["TableSizeBytes"]),
                    table["TableStatus"],
                )
            )

    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


check_info["aws_dynamodb_summary"] = LegacyCheckDefinition(
    name="aws_dynamodb_summary",
    parse_function=parse_aws,
    service_name="AWS/DynamoDB Summary",
    discovery_function=discover_aws_dynamodb_summary,
    check_function=check_aws_dynamodb_summary,
)
