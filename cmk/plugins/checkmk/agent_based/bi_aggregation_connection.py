#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


def parse_bi_aggregation_connection(string_table):
    import ast

    fields = ["missing_sites", "missing_aggr", "generic_errors"]
    parsed = {}
    for line in string_table:
        connection_info = ast.literal_eval(line[0])
        for field in fields:
            if connection_info[field]:
                parsed.setdefault(field, set()).update(connection_info[field])

    return parsed


def discover_bi_aggregation_connection(section: Any) -> DiscoveryResult:
    yield Service()


def check_bi_aggregation_connection(section: Any) -> CheckResult:
    if section.get("missing_sites"):
        yield Result(
            state=State.WARN,
            summary="Unable to query data from site(s): %s" % ", ".join(section["missing_sites"]),
        )
    if section.get("missing_aggr"):
        yield Result(
            state=State.WARN,
            summary="Unable to display aggregations because of missing data: %s"
            % ", ".join(section["missing_aggr"]),
        )
    if section.get("generic_errors"):
        yield Result(
            state=State.WARN,
            summary="Error during data collection: %s" % ", ".join(section["generic_errors"]),
        )

    if not section:
        yield Result(state=State.OK, summary="No connection problems")


agent_section_bi_aggregation_connection = AgentSection(
    name="bi_aggregation_connection", parse_function=parse_bi_aggregation_connection
)
check_plugin_bi_aggregation_connection = CheckPlugin(
    name="bi_aggregation_connection",
    service_name="BI Datasource Connection",
    discovery_function=discover_bi_aggregation_connection,
    check_function=check_bi_aggregation_connection,
)
