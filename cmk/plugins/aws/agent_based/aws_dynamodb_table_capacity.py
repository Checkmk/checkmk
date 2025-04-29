#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckResult,
    IgnoreResultsError,
    LevelsT,
    Metric,
    render,
    Result,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import (
    aws_get_float_human_readable,
    extract_aws_metrics_by_labels,
    parse_aws,
)


def _check_capacity_minmax_metrics(
    params: Mapping[str, Mapping], section: Mapping[str, float], to_check: str
) -> CheckResult:
    metric_ids = [f"Minimum_Consumed{to_check}", f"Maximum_Consumed{to_check}"]
    info_names = ["Min. single-request consumption", "Max. single-request consumption"]
    params_keys = ["levels_minimum", "levels_maximum"]

    for metric_id, label, params_key in zip(metric_ids, info_names, params_keys):
        metric_val = section.get(metric_id)

        if metric_val is not None:
            metric_name, unit = aws_dynamodb_capacity_get_metric_name_and_unit(metric_id)
            levels_upper, levels_lower = aws_capacity_params_to_levels(params.get(params_key, {}))
            yield from check_levels(
                value=metric_val,
                metric_name=metric_name,
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                label=label,
                render_func=lambda f: aws_get_float_human_readable(f, unit=unit),
            )


def aws_dynamodb_table_check_capacity(
    params: Mapping[str, Mapping], section: Mapping[str, float], capacity_units_to_check: str
) -> CheckResult:
    metric_id_avg = f"Sum_Consumed{capacity_units_to_check}"
    metric_val_avg = section.get(metric_id_avg)

    if metric_val_avg is None:
        raise IgnoreResultsError("Currently no data from AWS")

    metric_name, unit = aws_dynamodb_capacity_get_metric_name_and_unit(metric_id_avg)
    human_readable_avg = aws_get_float_human_readable(metric_val_avg, unit=unit)

    yield Result(
        state=State.OK,
        summary=f"Avg. consumption: {human_readable_avg}",
    )
    yield Metric(
        name=metric_name,
        value=metric_val_avg,
    )

    params_avg = params.get("levels_average", {})
    limit_val = params_avg.get("limit")
    if limit_val is None:
        limit_val = section.get(f"provisioned_{capacity_units_to_check}")

    if limit_val:
        perc_avg = metric_val_avg / limit_val * 100
        levels_upper, levels_lower = aws_capacity_params_to_levels(params_avg)
        yield from check_levels(
            value=perc_avg,
            metric_name=f"{metric_name}_perc",
            label="Usage",
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            render_func=render.percent,
        )

    yield from _check_capacity_minmax_metrics(params, section, capacity_units_to_check)


def aws_capacity_params_to_levels(params: Mapping[str, tuple]) -> tuple[LevelsT, LevelsT]:
    return (
        _capacity_params_to_level(params, "levels_upper"),
        _capacity_params_to_level(params, "levels_lower"),
    )


def _capacity_params_to_level(params: Mapping[str, tuple], key: str) -> LevelsT:
    if all(val is None for val in params[key]):
        return ("no_levels", None)

    if len(params[key]) == 2:
        return ("fixed", (params[key][0], params[key][1]))

    return ("no_levels", None)


def aws_dynamodb_capacity_get_metric_name_and_unit(metric_id: str) -> tuple[str, str]:
    if metric_id.startswith("Sum"):
        metric_id = metric_id.split("_")[-1]
    metric_lower = (
        metric_id.lower().replace("readcapacityunits", "_rcu").replace("writecapacityunits", "_wcu")
    )
    return f"aws_dynamodb_{metric_lower}", metric_lower[-3:].upper()


def parse_aws_dynamodb_table(string_table: StringTable) -> Mapping[str, float]:
    parsed = parse_aws(string_table)

    # the last entry contains the provisioned limits
    metrics = extract_aws_metrics_by_labels(
        [
            "Minimum_ConsumedReadCapacityUnits",
            "Maximum_ConsumedReadCapacityUnits",
            "Sum_ConsumedReadCapacityUnits",
            "Minimum_ConsumedWriteCapacityUnits",
            "Maximum_ConsumedWriteCapacityUnits",
            "Sum_ConsumedWriteCapacityUnits",
            "Query_Maximum_SuccessfulRequestLatency",
            "Query_Average_SuccessfulRequestLatency",
            "GetItem_Maximum_SuccessfulRequestLatency",
            "GetItem_Average_SuccessfulRequestLatency",
            "PutItem_Maximum_SuccessfulRequestLatency",
            "PutItem_Average_SuccessfulRequestLatency",
        ],
        parsed[:-1],
    )

    try:
        metrics = list(metrics.values())[-1]
        metrics.update(parsed[-1])
        return metrics
    except IndexError:
        return {}


agent_section_aws_dynamodb_table = AgentSection(
    name="aws_dynamodb_table",
    parse_function=parse_aws_dynamodb_table,
)
