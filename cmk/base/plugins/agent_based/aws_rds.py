#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Dict,
    Mapping,
)
from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.aws import (
    AWSSectionMetrics,
    aws_rds_service_item,
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
            extra_keys=['DBInstanceIdentifier', 'AllocatedStorage', 'Region'],
    ).values():

        try:
            metrics['AllocatedStorage'] *= 1.074e+9
        except KeyError:
            pass

        section.setdefault(
            aws_rds_service_item(metrics['DBInstanceIdentifier'], metrics['Region']),
            metrics,
        )
    return section


register.agent_section(
    name="aws_rds",
    parse_function=parse_aws_rds,
)
