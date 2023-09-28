#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping
from typing import Any

from cmk.base.plugins.agent_based.utils.diskstat import check_diskstat_dict

from .agent_based_api.v1 import check_levels, get_rate, get_value_store, register, render
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.aws import discover_aws_generic, extract_aws_metrics_by_labels, parse_aws

Section = Mapping[str, Mapping[str, float]]


def parse_aws_ebs(string_table: StringTable) -> Section:
    """
    >>> parse_aws_ebs([[
    ... '[{"Id":', '"id_10_VolumeReadOps",', '"Label":', '"123",',
    ... '"Timestamps":', '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0030055,', 'null]],',
    ... '"StatusCode":', '"Complete"}]']])
    {'123': {'VolumeReadOps': 0.0030055}}
    """
    return extract_aws_metrics_by_labels(
        [
            "VolumeReadOps",
            "VolumeWriteOps",
            "VolumeReadBytes",
            "VolumeWriteBytes",
            "VolumeQueueLength",
            "BurstBalance",
            # "VolumeThroughputPercentage",
            # "VolumeConsumedReadWriteOps",
            # "VolumeTotalReadTime",
            # "VolumeTotalWriteTime",
            # "VolumeIdleTime",
        ],
        parse_aws(string_table),
    )


register.agent_section(
    name="aws_ebs",
    parse_function=parse_aws_ebs,
)

#   .--Disk IO-------------------------------------------------------------.
#   |                     ____  _     _      ___ ___                       |
#   |                    |  _ \(_)___| | __ |_ _/ _ \                      |
#   |                    | | | | / __| |/ /  | | | | |                     |
#   |                    | |_| | \__ \   <   | | |_| |                     |
#   |                    |____/|_|___/_|\_\ |___\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


def discover_aws_ebs(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(
        section,
        [
            "VolumeReadOps",
            "VolumeWriteOps",
            "VolumeReadBytes",
            "VolumeWriteBytes",
            "VolumeQueueLength",
        ],
    )


def check_aws_ebs(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    now = time.time()
    disk_data: Mapping[str, float] = {
        "read_ios": get_rate(
            get_value_store(),
            f"aws_ebs_disk_io_read_ios.{item}",
            now,
            disk["VolumeReadOps"],
        ),
        "write_ios": get_rate(
            get_value_store(),
            f"aws_ebs_disk_io_write_ios.{item}",
            now,
            disk["VolumeWriteOps"],
        ),
        "read_throughput": get_rate(
            get_value_store(),
            f"aws_ebs_disk_io_read_throughput.{item}",
            now,
            disk["VolumeReadBytes"],
        ),
        "write_throughput": get_rate(
            get_value_store(),
            f"aws_ebs_disk_io_write_throughput.{item}",
            now,
            disk["VolumeWriteBytes"],
        ),
        "queue_length": get_rate(
            get_value_store(),
            f"aws_ebs_disk_io_queue_len.{item}",
            now,
            disk["VolumeQueueLength"],
        ),
    }

    yield from check_diskstat_dict(
        params=params,
        disk=disk_data,
        value_store=get_value_store(),
        this_time=now,
    )


register.check_plugin(
    name="aws_ebs",
    service_name="AWS/EBS Disk IO %s",
    discovery_function=discover_aws_ebs,
    check_function=check_aws_ebs,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)

# .
#   .--burst balance-------------------------------------------------------.
#   |    _                    _     _           _                          |
#   |   | |__  _   _ _ __ ___| |_  | |__   __ _| | __ _ _ __   ___ ___     |
#   |   | '_ \| | | | '__/ __| __| | '_ \ / _` | |/ _` | '_ \ / __/ _ \    |
#   |   | |_) | |_| | |  \__ \ |_  | |_) | (_| | | (_| | | | | (_|  __/    |
#   |   |_.__/ \__,_|_|  |___/\__| |_.__/ \__,_|_|\__,_|_| |_|\___\___|    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_ebs_burst_balance(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(
        section,
        ["BurstBalance"],
    )


def check_aws_ebs_burst_balance(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if (disk_data := section.get(item)) is None:
        return

    yield from check_levels(
        value=disk_data["BurstBalance"],
        metric_name="aws_burst_balance",
        levels_lower=params.get("burst_balance_levels_lower", (None, None)),
        render_func=render.percent,
        label="Balance",
    )


register.check_plugin(
    name="aws_ebs_burst_balance",
    check_function=check_aws_ebs_burst_balance,
    discovery_function=discover_aws_ebs_burst_balance,
    sections=["aws_ebs"],
    check_default_parameters={},
    check_ruleset_name="aws_ebs_burst_balance",
    service_name="AWS/EBS Burst Balance %s",
)
