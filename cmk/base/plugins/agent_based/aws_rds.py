#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import get_value_store, IgnoreResultsError, register
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import interfaces
from .utils.aws import (
    aws_rds_service_item,
    AWSSectionMetrics,
    discover_aws_generic,
    extract_aws_metrics_by_labels,
    parse_aws,
)


def parse_aws_rds(string_table: StringTable) -> AWSSectionMetrics:
    section: Dict[str, Mapping[str, Any]] = {}
    for metrics in extract_aws_metrics_by_labels(
        [
            "CPUUtilization",
            "CPUCreditUsage",
            "CPUCreditBalance",
            "DatabaseConnections",
            "FailedSQLServerAgentJobsCount",
            "BinLogDiskUsage",
            "OldestReplicationSlotLag",
            "ReplicaLag",
            "ReplicationSlotDiskUsage",
            "TransactionLogsDiskUsage",
            "TransactionLogsGeneration",
            "NetworkReceiveThroughput",
            "NetworkTransmitThroughput",
            "DiskQueueDepth",
            "WriteIOPS",
            "WriteLatency",
            "WriteThroughput",
            "ReadIOPS",
            "ReadLatency",
            "ReadThroughput",
            "BurstBalance",
            # "FreeableMemory",
            # "SwapUsage",
            # "FreeStorageSpace",
            # "MaximumUsedTransactionIDs",
        ],
        parse_aws(string_table),
        extra_keys=["DBInstanceIdentifier", "AllocatedStorage", "Region"],
    ).values():

        try:
            metrics["AllocatedStorage"] *= 1.074e9
        except KeyError:
            pass

        section.setdefault(
            aws_rds_service_item(metrics["DBInstanceIdentifier"], metrics["Region"]),
            metrics,
        )
    return section


register.agent_section(
    name="aws_rds",
    parse_function=parse_aws_rds,
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


def discover_aws_rds_network_io(section: AWSSectionMetrics) -> DiscoveryResult:
    yield from discover_aws_generic(
        section,
        ["NetworkReceiveThroughput", "NetworkTransmitThroughput"],
    )


def check_aws_rds_network_io(
    item: str,
    params: Mapping[str, Any],
    section: AWSSectionMetrics,
) -> CheckResult:
    metrics = section.get(item)
    if metrics is None:
        return
    try:
        interface = interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            interfaces.InterfaceWithRates(
                attributes=interfaces.Attributes(
                    index="0",
                    descr=item,
                    alias=metrics.get("DBInstanceIdentifier", item),
                    type="1",
                    oper_status="1",
                ),
                rates=interfaces.Rates(
                    in_octets=metrics["NetworkReceiveThroughput"],
                    out_octets=metrics["NetworkTransmitThroughput"],
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


register.check_plugin(
    name="aws_rds_network_io",
    sections=["aws_rds"],
    service_name="AWS/RDS %s Network IO",
    discovery_function=discover_aws_rds_network_io,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_aws_rds_network_io,
)
