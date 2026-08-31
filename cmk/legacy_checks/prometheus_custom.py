#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)

type Section = Mapping[str, Any]
type _Levels = tuple[float, float] | None

ERROR_DETAILS = {
    "query error": "does not produce a valid result",
    "unsupported query": "produces more than one result (only one allowed)",
    "no value": "returns no value",
}


def parse_prometheus_custom(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}
    for line in string_table:
        try:
            prometheus_data = json.loads(line[0])
        except ValueError:
            continue
        parsed.update(prometheus_data)
    return parsed


def _check_for_invalid_result(
    metric_details: Mapping[str, Any], promql_expression: str
) -> Result | None:
    """Produces the output including service status and infotext for a invalid/failed
       PromQL query (and therefore service metric)

       This function also verifies if the given PromQL expression previously gave a valid output
       and has now become invalid due to changes on the Prometheus side

    Args:
        metric_details: Dict which contains the information of the metric including an error message
                        in case the PromQL query has failed
        promql_expression: String expression of the failed/invalid PromQL query

    Returns: None in case the query gave a valid output, or a Result reporting the failure

    """
    value_store = get_value_store()
    expression_has_been_valid_before = value_store.get(promql_expression, False)
    expression_is_valid_now = "value" in metric_details

    if expression_is_valid_now:
        # Keep a record of the PromQL expressions which gave a valid result at least once
        value_store[promql_expression] = True
        return None

    if expression_has_been_valid_before:
        state = State.WARN
        infotext = "previously valid is now invalid"
    else:
        state = State.CRIT
        infotext = ERROR_DETAILS[metric_details["invalid_info"]]
    return Result(state=state, summary=f"PromQL expression ({promql_expression}) {infotext}")


def _metric_levels(
    metric_label: str,
    datasource_levels: Mapping[str, Any] | None,
    service_levels: Sequence[Mapping[str, Any]],
) -> tuple[_Levels, _Levels]:
    """Retrieve the relevant check levels for the relevant service metric value

    Levels for Prometheus custom can be defined at two WATO places:
        1. In Datasource Programs directly next to the custom service definition
        2. In a separate WATO rule

    The WATO rule always has priority over the Datasource rule.

    Args:
        metric_label:
            The current metric label of the current custom Prometheus service

        datasource_levels:
            The datasource levels for the current service metric value

        service_levels:
            The separate defined WATO levels for the current service metric value

    Returns:
        The matching upper and lower levels

    """
    for metric_entry in service_levels:
        if metric_entry["metric_label"] == metric_label:
            metric_levels = metric_entry.get("levels", {})
            return metric_levels.get("upper_levels"), metric_levels.get("lower_levels")

    if datasource_levels:
        return datasource_levels.get("upper_levels"), datasource_levels.get("lower_levels")
    return None, None


def check_prometheus_custom(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    for metric_details in data["service_metrics"]:
        promql_expression = metric_details["promql_query"]
        metric_label = metric_details["label"]

        metric_name = metric_details.get("name")
        if metric_name == "null":
            metric_name = None

        if invalid_result := _check_for_invalid_result(metric_details, promql_expression):
            yield invalid_result
            continue

        levels_upper, levels_lower = _metric_levels(
            metric_label,
            metric_details.get("levels"),
            params["metric_list"],
        )
        yield from check_levels_v1(
            float(metric_details["value"]),
            metric_name=metric_name,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            label=metric_label,
        )


def discover_prometheus_custom(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_prometheus_custom = AgentSection(
    name="prometheus_custom",
    parse_function=parse_prometheus_custom,
)


check_plugin_prometheus_custom = CheckPlugin(
    name="prometheus_custom",
    service_name="%s",
    discovery_function=discover_prometheus_custom,
    check_function=check_prometheus_custom,
    check_ruleset_name="prometheus_custom",
    check_default_parameters={"metric_list": []},
)
