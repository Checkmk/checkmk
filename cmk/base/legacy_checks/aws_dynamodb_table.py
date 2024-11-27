#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.aws import (
    aws_get_float_human_readable,
    inventory_aws_generic_single,
)

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render
from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, parse_aws

check_info = {}


def parse_aws_dynamodb_table(string_table):
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


check_info["aws_dynamodb_table"] = LegacyCheckDefinition(
    name="aws_dynamodb_table",
    parse_function=parse_aws_dynamodb_table,
)


def _capacity_metric_id_to_name_and_unit(metric_id):
    if metric_id.startswith("Sum"):
        metric_id = metric_id.split("_")[-1]
    metric_name = "aws_dynamodb_%s" % metric_id.lower().replace(
        "readcapacityunits", "_rcu"
    ).replace("writecapacityunits", "_wcu")
    unit = metric_name[-3:].upper()
    return metric_name, unit


def _capacity_params_to_levels(params):
    return params.get("levels_upper", (None, None)) + params.get("levels_lower", (None, None))


def _check_capacity_minmax_metrics(params, parsed, to_check):
    metric_ids = ["Minimum_Consumed%s" % to_check, "Maximum_Consumed%s" % to_check]
    info_names = ["Min. single-request consumption", "Max. single-request consumption"]
    params_keys = ["levels_minimum", "levels_maximum"]

    for metric_id, infoname, params_key in zip(metric_ids, info_names, params_keys):
        metric_val = parsed.get(metric_id)

        if metric_val is not None:
            metric_name, unit = _capacity_metric_id_to_name_and_unit(metric_id)

            yield check_levels(
                metric_val,
                metric_name,
                _capacity_params_to_levels(params.get(params_key, {})),
                infoname=infoname,
                human_readable_func=lambda f, _u=unit: aws_get_float_human_readable(f, unit=_u),
            )


def _check_aws_dynamodb_capacity(params, parsed, capacity_units_to_check):
    metric_id_avg = "Sum_Consumed%s" % capacity_units_to_check
    metric_val_avg = parsed.get(metric_id_avg)

    if metric_val_avg is None:
        raise IgnoreResultsError("Currently no data from AWS")

    metric_name, unit = _capacity_metric_id_to_name_and_unit(metric_id_avg)

    yield (
        0,
        "Avg. consumption: %s" % aws_get_float_human_readable(metric_val_avg, unit=unit),
        [(metric_name, metric_val_avg)],
    )

    params_avg = params.get("levels_average", {})
    limit_val = params_avg.get("limit")
    if limit_val is None:
        limit_val = parsed["provisioned_%s" % capacity_units_to_check]

    if limit_val:
        perc_avg = metric_val_avg / limit_val * 100
        yield check_levels(
            perc_avg,
            metric_name + "_perc",
            _capacity_params_to_levels(params_avg),
            infoname="Usage",
            human_readable_func=render.percent,
        )

    yield from _check_capacity_minmax_metrics(params, parsed, capacity_units_to_check)


def check_aws_dynamodb_read_capacity(item, params, parsed):
    yield from _check_aws_dynamodb_capacity(
        params.get("levels_read", {}), parsed, "ReadCapacityUnits"
    )


def check_aws_dynamodb_write_capacity(item, params, parsed):
    yield from _check_aws_dynamodb_capacity(
        params.get("levels_write", {}), parsed, "WriteCapacityUnits"
    )


def inventory_aws_dynamodb_latency(parsed):
    return inventory_aws_generic_single(
        parsed,
        [
            "Query_Average_SuccessfulRequestLatency",
            "GetItem_Average_SuccessfulRequestLatency",
            "PutItem_Average_SuccessfulRequestLatency",
        ],
        requirement=any,
    )


def check_aws_dynamodb_latency(item, params, parsed):
    go_stale = True

    for operation in ["Query", "GetItem", "PutItem"]:
        for statistic in ["Average", "Maximum"]:
            metric_name = f"aws_dynamodb_{operation.lower()}_{statistic.lower()}_latency"
            metric_id = f"{operation}_{statistic}_SuccessfulRequestLatency"
            metric_val = parsed.get(metric_id)

            if metric_val is not None:
                go_stale = False

                # SuccessfulRequestLatency and levels come in ms
                metric_val *= 1e-3
                levels = params.get(f"levels_seconds_{operation.lower()}_{statistic.lower()}")
                if levels is not None:
                    levels = tuple(level * 1e-3 for level in levels)

                yield check_levels(
                    metric_val,
                    metric_name,
                    levels,
                    infoname=f"{statistic} latency {operation}",
                    human_readable_func=render.timespan,
                )

    if go_stale:
        raise IgnoreResultsError("Currently no data from AWS")


def discover_aws_dynamodb_table_read_capacity(p):
    return inventory_aws_generic_single(p, ["Sum_ConsumedReadCapacityUnits"])


check_info["aws_dynamodb_table.read_capacity"] = LegacyCheckDefinition(
    name="aws_dynamodb_table_read_capacity",
    service_name="AWS/DynamoDB Read Capacity",
    sections=["aws_dynamodb_table"],
    discovery_function=discover_aws_dynamodb_table_read_capacity,
    check_function=check_aws_dynamodb_read_capacity,
    check_ruleset_name="aws_dynamodb_capacity",
    check_default_parameters={
        "levels_read": {
            "levels_average": {
                "levels_upper": (80.0, 90.0),
            },
        },
        "levels_write": {
            "levels_average": {
                "levels_upper": (80.0, 90.0),
            },
        },
    },
)


def discover_aws_dynamodb_table_write_capacity(p):
    return inventory_aws_generic_single(p, ["Sum_ConsumedWriteCapacityUnits"])


check_info["aws_dynamodb_table.write_capacity"] = LegacyCheckDefinition(
    name="aws_dynamodb_table_write_capacity",
    service_name="AWS/DynamoDB Write Capacity",
    sections=["aws_dynamodb_table"],
    discovery_function=discover_aws_dynamodb_table_write_capacity,
    check_function=check_aws_dynamodb_write_capacity,
    check_ruleset_name="aws_dynamodb_capacity",
    check_default_parameters={
        "levels_read": {
            "levels_average": {
                "levels_upper": (80.0, 90.0),
            },
        },
        "levels_write": {
            "levels_average": {
                "levels_upper": (80.0, 90.0),
            },
        },
    },
)

check_info["aws_dynamodb_table.latency"] = LegacyCheckDefinition(
    name="aws_dynamodb_table_latency",
    service_name="AWS/DynamoDB Latency",
    sections=["aws_dynamodb_table"],
    discovery_function=inventory_aws_dynamodb_latency,
    check_function=check_aws_dynamodb_latency,
    check_ruleset_name="aws_dynamodb_latency",
)
