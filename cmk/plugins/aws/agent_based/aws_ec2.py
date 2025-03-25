#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    Result,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import (
    aws_host_labels,
    AWSMetric,
    check_aws_metrics,
    discover_aws_generic,
    discover_aws_generic_single,
    extract_aws_metrics_by_labels,
    parse_aws,
    parse_aws_labels,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy

Section = Mapping[str, float]

EC2DefaultItemName = "Summary"


def parse_aws_ec2(string_table: StringTable) -> Section:
    """
    >>> parse_aws_ec2([[
    ... '[{"Id":', '"id_10_CPUCreditUsage",', '"Label":', '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",',
    ... '"Timestamps":', '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0030055,', 'null]],',
    ... '"StatusCode":', '"Complete"}]']])
    {'CPUCreditUsage': 0.0030055}
    """
    metrics = extract_aws_metrics_by_labels(
        [
            "CPUCreditUsage",
            "CPUCreditBalance",
            "CPUUtilization",
            "DiskReadOps",
            "DiskWriteOps",
            "DiskReadBytes",
            "DiskWriteBytes",
            "NetworkIn",
            "NetworkOut",
            "StatusCheckFailed_Instance",
            "StatusCheckFailed_System",
        ],
        parse_aws(string_table),
    )
    # We get exactly one entry: {INST-ID: METRICS}
    # INST-ID is the piggyback host name
    try:
        inst_metrics = list(metrics.values())[-1]
    except IndexError:
        inst_metrics = {}
    return inst_metrics


agent_section_aws_ec2 = AgentSection(
    name="aws_ec2",
    parse_function=parse_aws_ec2,
)

agent_section_ec2_labels = AgentSection(
    name="ec2_labels",
    parse_function=parse_aws_labels,
    host_label_function=aws_host_labels,
)

#   .--status check--------------------------------------------------------.
#   |           _        _                    _               _            |
#   |       ___| |_ __ _| |_ _   _ ___    ___| |__   ___  ___| | __        |
#   |      / __| __/ _` | __| | | / __|  / __| '_ \ / _ \/ __| |/ /        |
#   |      \__ \ || (_| | |_| |_| \__ \ | (__| | | |  __/ (__|   <         |
#   |      |___/\__\__,_|\__|\__,_|___/  \___|_| |_|\___|\___|_|\_\        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                            main check                                |
#   '----------------------------------------------------------------------'


def discover_aws_ec2(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        [
            "StatusCheckFailed_System",
            "StatusCheckFailed_Instance",
        ],
    )


def check_aws_ec2_status_check(
    section: Section,
) -> CheckResult:
    key_pairs: Mapping[str, str] = {
        "System": "StatusCheckFailed_System",
        "Instance": "StatusCheckFailed_Instance",
    }

    go_stale = True
    for key, section_key in key_pairs.items():
        if (value := section.get(section_key)) is None:
            continue

        yield (
            Result(state=State.OK, summary=f"{key}: Passed")
            if value < 1.0
            else Result(state=State.CRIT, summary=f"{key}: Failed")
        )
        go_stale = False

    if go_stale:
        raise IgnoreResultsError("Currently no data from AWS")


check_plugin_aws_ec2 = CheckPlugin(
    name="aws_ec2",
    check_function=check_aws_ec2_status_check,
    discovery_function=discover_aws_ec2,
    service_name="AWS/EC2 Status Check",
)

# .
#   .--network IO----------------------------------------------------------.
#   |                     _                      _      ___ ___            |
#   |          _ __   ___| |___      _____  _ __| | __ |_ _/ _ \           |
#   |         | '_ \ / _ \ __\ \ /\ / / _ \| '__| |/ /  | | | | |          |
#   |         | | | |  __/ |_ \ V  V / (_) | |  |   <   | | |_| |          |
#   |         |_| |_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |___\___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_ec2_network_io(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(
        {EC2DefaultItemName: section},
        ["NetworkIn", "NetworkOut"],
    )


def check_aws_ec2_network_io(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    try:
        interface = interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            interfaces.InterfaceWithRates(
                attributes=interfaces.Attributes(
                    index="0",
                    descr=item,
                    alias=item,
                    type="1",
                    oper_status="1",
                ),
                rates=interfaces.Rates(
                    in_octets=section["NetworkIn"] / 60,
                    out_octets=section["NetworkOut"] / 60,
                ),
                get_rate_errors=[],
            ),
            timestamp=time.time(),
            value_store=get_value_store(),
            params=params,
        )
    except KeyError:
        raise IgnoreResultsError("Currently no data from AWS")
    yield from interfaces.check_single_interface(item, params, interface)


check_plugin_aws_ec2_network_io = CheckPlugin(
    name="aws_ec2_network_io",
    sections=["aws_ec2"],
    service_name="AWS/EC2 Network IO %s",
    discovery_function=discover_aws_ec2_network_io,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_aws_ec2_network_io,
)

# .
#   .--disk IO-------------------------------------------------------------.
#   |                         _ _     _      ___ ___                       |
#   |                      __| (_)___| | __ |_ _/ _ \                      |
#   |                     / _` | / __| |/ /  | | | | |                     |
#   |                    | (_| | \__ \   <   | | |_| |                     |
#   |                     \__,_|_|___/_|\_\ |___\___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# It would be better to use metrics with the statistics "Sum" instead of "Average" for this check
# (since we want to compute rates). However, this is does not seem to be possible here. AWS
# publishes the EC2 metrics at 5-minute intervals, whereby each published datapoint consists of 5
# 1-minute datapoints (one can check this using the statistics "SampleCount", which gives the number
# of data points in the specified interval). If we request one of the metrics used below for the
# last 600s (which is what the agent does), we should get a SampleCount of 10, however, we will
# only get a sample count of 5. Hence, if we used the "Sum" statistics, we would be dividing a sum
# corresponding to a 5-minute interval by 10 minutes. Note that this problem does not occur when
# collecting the metrics for a 10-minute interval further in the past (for example from -20 min to
# -10 min).


def discover_aws_ec2_disk_io(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(
        {EC2DefaultItemName: section},
        [
            "DiskReadOps",
            "DiskWriteOps",
            "DiskReadBytes",
            "DiskWriteBytes",
        ],
    )


def check_aws_ec2_disk_io(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    disk_data: dict[str, float] = {}
    key_pairs: Mapping[
        str, str
    ] = {  # The key from the Mapping is the result that we want and the value is how we get the data
        "read_ios": "DiskReadOps",
        "write_ios": "DiskWriteOps",
        "read_throughput": "DiskReadBytes",
        "write_throughput": "DiskWriteBytes",
    }

    for key, section_key in key_pairs.items():
        if (value := section.get(section_key)) is None:
            continue

        disk_data[key] = value / 60.0

    if not disk_data:
        raise IgnoreResultsError("Currently no data from AWS")

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk_data,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_aws_ec2_disk_io = CheckPlugin(
    name="aws_ec2_disk_io",
    check_function=check_aws_ec2_disk_io,
    discovery_function=discover_aws_ec2_disk_io,
    check_default_parameters={},
    check_ruleset_name="diskstat",
    service_name="AWS/EC2 Disk IO %s",
    sections=["aws_ec2"],
)

# .
#   .--CPU utilization-----------------------------------------------------.
#   |    ____ ____  _   _         _   _ _ _          _   _                 |
#   |   / ___|  _ \| | | |  _   _| |_(_) (_)______ _| |_(_) ___  _ __      |
#   |  | |   | |_) | | | | | | | | __| | | |_  / _` | __| |/ _ \| '_ \     |
#   |  | |___|  __/| |_| | | |_| | |_| | | |/ / (_| | |_| | (_) | | | |    |
#   |   \____|_|    \___/   \__,_|\__|_|_|_/___\__,_|\__|_|\___/|_| |_|    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_ec2_cpu_util(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["CPUUtilization"],
    )


def check_aws_ec2_cpu_util(params: Mapping[str, Any], section: Section) -> CheckResult:
    if (cpu_utilization_value := section.get("CPUUtilization")) is None:
        raise IgnoreResultsError("Currently no data from AWS")

    yield from check_cpu_util(
        util=cpu_utilization_value,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_aws_ec2_cpu_util = CheckPlugin(
    name="aws_ec2_cpu_util",
    check_function=check_aws_ec2_cpu_util,
    discovery_function=discover_aws_ec2_cpu_util,
    service_name="AWS/EC2 CPU utilization",
    check_default_parameters={"util": (90.0, 95.0)},
    sections=["aws_ec2"],
    check_ruleset_name="cpu_utilization",
)

# .
#   .--CPU credits---------------------------------------------------------.
#   |           ____ ____  _   _                     _ _ _                 |
#   |          / ___|  _ \| | | |   ___ _ __ ___  __| (_) |_ ___           |
#   |         | |   | |_) | | | |  / __| '__/ _ \/ _` | | __/ __|          |
#   |         | |___|  __/| |_| | | (__| | |  __/ (_| | | |_\__ \          |
#   |          \____|_|    \___/   \___|_|  \___|\__,_|_|\__|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_ec2_cpu_credits(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["CPUCreditUsage", "CPUCreditBalance"],
    )


def check_aws_ec2_cpu_credits(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=name,
                levels_lower=levels_lower,
                label=label,
            )
            for metric_name, name, levels_lower, label in zip(
                ["CPUCreditUsage", "CPUCreditBalance"],
                [None, "aws_cpu_credit_balance"],
                [None, params.get("balance_levels_lower")],
                ["Usage", "Balance"],
            )
            if (value := section.get(metric_name)) is not None
        ]
    )


check_plugin_aws_ec2_cpu_credits = CheckPlugin(
    name="aws_ec2_cpu_credits",
    service_name="AWS/EC2 CPU Credits",
    check_function=check_aws_ec2_cpu_credits,
    discovery_function=discover_aws_ec2_cpu_credits,
    check_default_parameters={"balance_levels_lower": (10, 5)},
    check_ruleset_name="aws_ec2_cpu_credits",
    sections=["aws_ec2"],
)
