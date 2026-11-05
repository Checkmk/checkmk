#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Generator, Mapping, MutableMapping
from contextlib import contextmanager, suppress
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    render,
    Result,
    State,
    StringTable,
)
from cmk.plugins.aws_v2.lib import (
    aws_get_counts_rate_human_readable,
    aws_rds_service_item,
    discover_aws_generic_single,
    extract_aws_metrics_by_labels,
    parse_aws,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy


@contextmanager
def _ignore_results_if_missing_data() -> Generator[None]:
    try:
        yield
    except KeyError as exc:
        raise IgnoreResultsError("Currently no data from AWS") from exc


Section = Mapping[str, Any]
"""The metrics of one instance, with its ID, region and allocated storage"""


def parse_aws_rds(string_table: StringTable) -> Section | None:
    instances: list[MutableMapping[str, Any]] = []
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
        with suppress(KeyError):
            metrics["AllocatedStorage"] *= 1.074e9
        instances.append(metrics)
    # Each instance is a host of its own, so the section has the metrics of one instance.
    return next(iter(instances), None)


agent_section_aws_v2_rds = AgentSection(
    name="aws_v2_rds",
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


def discover_aws_rds_network_io(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["NetworkReceiveThroughput", "NetworkTransmitThroughput"],
    )


def check_aws_rds_network_io(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        # The interface keeps the name that was the item, so the output does not change.
        name = aws_rds_service_item(section["DBInstanceIdentifier"], section["Region"])
        interface = interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            interfaces.InterfaceWithRates(
                attributes=interfaces.Attributes(
                    index="0",
                    descr=name,
                    alias=section["DBInstanceIdentifier"],
                    type="1",
                    oper_status="1",
                ),
                rates=interfaces.Rates(
                    in_octets=section["NetworkReceiveThroughput"],
                    out_octets=section["NetworkTransmitThroughput"],
                ),
                get_rate_errors=[],
                timestamp=time.time(),
            ),
            value_store=get_value_store(),
            params=params,
        )

    yield from interfaces.check_single_interface(name, params, interface)


check_plugin_aws_v2_rds_network_io = CheckPlugin(
    name="aws_v2_rds_network_io",
    sections=["aws_v2_rds"],
    service_name="AWS/RDS Network IO",
    discovery_function=discover_aws_rds_network_io,
    check_ruleset_name="aws_v2_rds_network_io",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_aws_rds_network_io,
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


def discover_aws_rds_disk_io(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        [
            "DiskQueueDepth",
            "ReadIOPS",
            "ReadLatency",
            "ReadThroughput",
            "WriteIOPS",
            "WriteLatency",
            "WriteThroughput",
        ],
    )


def check_aws_rds_disk_io(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    disk_data: MutableMapping[str, float] = {}

    for key, metric_key, scale in [
        ("read_ios", "ReadIOPS", 1.0),
        ("write_ios", "WriteIOPS", 1.0),
        ("read_throughput", "ReadThroughput", 1.0),
        ("write_throughput", "WriteThroughput", 1.0),
        ("read_latency", "ReadLatency", 1000.0),
        ("write_latency", "WriteLatency", 1000.0),
    ]:
        if (metric := section.get(metric_key)) is None:
            continue
        disk_data[key] = metric * scale

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk_data,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_aws_v2_rds_disk_io = CheckPlugin(
    name="aws_v2_rds_disk_io",
    service_name="AWS/RDS Disk IO",
    check_function=check_aws_rds_disk_io,
    discovery_function=discover_aws_rds_disk_io,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_disk_io",
    sections=["aws_v2_rds"],
)


#   .--CPU utilization-----------------------------------------------------.
#   |    ____ ____  _   _         _   _ _ _          _   _                 |
#   |   / ___|  _ \| | | |  _   _| |_(_) (_)______ _| |_(_) ___  _ __      |
#   |  | |   | |_) | | | | | | | | __| | | |_  / _` | __| |/ _ \| '_ \     |
#   |  | |___|  __/| |_| | | |_| | |_| | | |/ / (_| | |_| | (_) | | | |    |
#   |   \____|_|    \___/   \__,_|\__|_|_|_/___\__,_|\__|_|\___/|_| |_|    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_rds(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["CPUUtilization"],
    )


def check_aws_rds(params: Mapping[str, Any], section: Section) -> CheckResult:
    with _ignore_results_if_missing_data():
        yield from check_cpu_util(
            util=section["CPUUtilization"],
            params=params,
            value_store=get_value_store(),
            this_time=time.time(),
        )


check_plugin_aws_v2_rds = CheckPlugin(
    name="aws_v2_rds",
    service_name="AWS/RDS CPU Utilization",
    check_default_parameters={"levels": (80.0, 90.0)},
    check_ruleset_name="aws_v2_rds_cpu_utilization",
    check_function=check_aws_rds,
    discovery_function=discover_aws_rds,
)

# .
#   .--agent jobs----------------------------------------------------------.
#   |                                 _       _       _                    |
#   |           __ _  __ _  ___ _ __ | |_    (_) ___ | |__  ___            |
#   |          / _` |/ _` |/ _ \ '_ \| __|   | |/ _ \| '_ \/ __|           |
#   |         | (_| | (_| |  __/ | | | |_    | | (_) | |_) \__ \           |
#   |          \__,_|\__, |\___|_| |_|\__|  _/ |\___/|_.__/|___/           |
#   |                |___/                 |__/                            |
#   '----------------------------------------------------------------------'


def discover_aws_rds_agent_jobs(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["FailedSQLServerAgentJobsCount"],
    )


def check_aws_rds_agent_jobs(section: Section) -> CheckResult:
    with _ignore_results_if_missing_data():
        failed_agent_jobs = section["FailedSQLServerAgentJobsCount"]

    if failed_agent_jobs > 0:
        yield Result(
            state=State.WARN,
            summary=f"Rate of failing jobs: {aws_get_counts_rate_human_readable(failed_agent_jobs)}",
        )
        return

    yield Result(
        state=State.OK,
        summary=f"Rate of failing jobs: {aws_get_counts_rate_human_readable(failed_agent_jobs)}",
    )


check_plugin_aws_v2_rds_agent_jobs = CheckPlugin(
    name="aws_v2_rds_agent_jobs",
    service_name="AWS/RDS SQL Server Agent Jobs",
    check_function=check_aws_rds_agent_jobs,
    discovery_function=discover_aws_rds_agent_jobs,
    sections=["aws_v2_rds"],
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

# CPU credit balance:
# For standard T2 instances with bursting, a burst can continue only as long as
# there are available CPU credits, so it’s important to monitor your instance’s
# balance. Credits are earned any time the instance is running below its baseline
# CPU performance level. The initial balance, accrual rate, and maximum possible
# balance are all dependent on the instance level.
#
# CPU credit usage:
# One CPU credit is equivalent to one minute of 100 percent CPU utilization (or
# two minutes at 50 percent, etc.). Whenever an instance requires CPU performance
# above that instance type’s baseline, it will burst, consuming CPU credits until
# the demand lessens or the credit balance runs out. Keeping an eye on your
# instances’ credit usage will help you identify whether you might need to switch
# to an instance type that is optimized for CPU-intensive workloads. Or, you can
# create an alert for when your credit balance drops below a threshold while CPU
# usage remains above baseline.


def discover_aws_rds_cpu_credits(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        [
            "CPUCreditUsage",
            "CPUCreditBalance",
        ],
    )


def check_aws_rds_cpu_credits(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        cpu_credit_usage = section["CPUCreditUsage"]
        cpu_credit_balance = section["CPUCreditBalance"]

    yield Result(state=State.OK, summary=f"CPU Credit Usage: {cpu_credit_usage:.2f}")

    yield from check_levels_v1(
        value=cpu_credit_balance,
        metric_name="aws_cpu_credit_balance",
        levels_lower=params.get("balance_levels_lower", (None, None)),
        label="CPU Credit Balance",
    )

    if burst_balance := section.get("BurstBalance"):
        yield from check_levels_v1(
            value=burst_balance,
            metric_name="aws_burst_balance",
            levels_lower=params.get("burst_balance_levels_lower", (None, None)),
            render_func=render.percent,
            label="Burst Balance",
        )


check_plugin_aws_v2_rds_cpu_credits = CheckPlugin(
    name="aws_v2_rds_cpu_credits",
    service_name="AWS/RDS CPU Credits",
    check_function=check_aws_rds_cpu_credits,
    discovery_function=discover_aws_rds_cpu_credits,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_cpu_credits",
    sections=["aws_v2_rds"],
)

# .
#   .--bin log usage-------------------------------------------------------.
#   |     _     _         _                                                |
#   |    | |__ (_)_ __   | | ___   __ _   _   _ ___  __ _  __ _  ___       |
#   |    | '_ \| | '_ \  | |/ _ \ / _` | | | | / __|/ _` |/ _` |/ _ \      |
#   |    | |_) | | | | | | | (_) | (_| | | |_| \__ \ (_| | (_| |  __/      |
#   |    |_.__/|_|_| |_| |_|\___/ \__, |  \__,_|___/\__,_|\__, |\___|      |
#   |                             |___/                   |___/            |
#   '----------------------------------------------------------------------'


def discover_aws_rds_bin_log_usage(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["BinLogDiskUsage"],
    )


def check_aws_rds_bin_log_usage(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        bin_log_usage = section["BinLogDiskUsage"]

    yield Result(state=State.OK, summary=render.bytes(bin_log_usage))

    if (allocated_storage := section.get("AllocatedStorage")) is None or allocated_storage == 0.0:
        yield Result(state=State.WARN, summary="Cannot calculate usage")
        return

    usage = 100.0 * bin_log_usage / allocated_storage
    yield from check_levels_v1(
        value=usage,
        metric_name="aws_rds_bin_log_disk_usage",
        levels_upper=params.get("levels"),
        render_func=render.percent,
    )


check_plugin_aws_v2_rds_bin_log_usage = CheckPlugin(
    name="aws_v2_rds_bin_log_usage",
    check_function=check_aws_rds_bin_log_usage,
    discovery_function=discover_aws_rds_bin_log_usage,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_disk_usage",
    service_name="AWS/RDS Binary Log Usage",
    sections=["aws_v2_rds"],
)

# .
#   .--transaction logs usage----------------------------------------------.
#   |        _                                  _   _                      |
#   |       | |_ _ __ __ _ _ __  ___  __ _  ___| |_(_) ___  _ __           |
#   |       | __| '__/ _` | '_ \/ __|/ _` |/ __| __| |/ _ \| '_ \          |
#   |       | |_| | | (_| | | | \__ \ (_| | (__| |_| | (_) | | | |         |
#   |        \__|_|  \__,_|_| |_|___/\__,_|\___|\__|_|\___/|_| |_|         |
#   |                                                                      |
#   |           _                                                          |
#   |          | | ___   __ _ ___   _   _ ___  __ _  __ _  ___             |
#   |          | |/ _ \ / _` / __| | | | / __|/ _` |/ _` |/ _ \            |
#   |          | | (_) | (_| \__ \ | |_| \__ \ (_| | (_| |  __/            |
#   |          |_|\___/ \__, |___/  \__,_|___/\__,_|\__, |\___|            |
#   |                   |___/                       |___/                  |
#   '----------------------------------------------------------------------'


def discover_aws_rds_transaction_logs_usage(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["TransactionLogsDiskUsage"],
    )


def check_aws_rds_transaction_logs_usage(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        transaction_logs_space = section["TransactionLogsDiskUsage"]

    yield Result(
        state=State.OK,
        summary=render.bytes(transaction_logs_space),
    )

    if (allocated_storage := section.get("AllocatedStorage")) is None or allocated_storage == 0.0:
        yield Result(
            state=State.WARN,
            summary="Cannot calculate usage",
        )
        return

    usage = 100.0 * transaction_logs_space / allocated_storage
    yield from check_levels_v1(
        value=usage,
        metric_name="aws_rds_transaction_logs_disk_usage",
        levels_upper=params.get("levels"),
        render_func=render.percent,
    )

    if generation := section.get("TransactionLogsGeneration"):
        yield Result(
            state=State.OK,
            summary=f"Generation rate: {render.iobandwidth(generation)}",
        )


check_plugin_aws_v2_rds_transaction_logs_usage = CheckPlugin(
    name="aws_v2_rds_transaction_logs_usage",
    service_name="AWS/RDS Transaction Logs Usage",
    check_function=check_aws_rds_transaction_logs_usage,
    discovery_function=discover_aws_rds_transaction_logs_usage,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_disk_usage",
    sections=["aws_v2_rds"],
)

# .
#   .--replication slot usage----------------------------------------------.
#   |                 _ _           _   _                   _       _      |
#   |  _ __ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __    ___| | ___ | |_    |
#   | | '__/ _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \  / __| |/ _ \| __|   |
#   | | | |  __/ |_) | | | (_| (_| | |_| | (_) | | | | \__ \ | (_) | |_    |
#   | |_|  \___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_| |___/_|\___/ \__|   |
#   |          |_|                                                         |
#   |                                                                      |
#   |                     _   _ ___  __ _  __ _  ___                       |
#   |                    | | | / __|/ _` |/ _` |/ _ \                      |
#   |                    | |_| \__ \ (_| | (_| |  __/                      |
#   |                     \__,_|___/\__,_|\__, |\___|                      |
#   |                                     |___/                            |
#   '----------------------------------------------------------------------'


def discover_aws_rds_replication_slot_usage(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["ReplicationSlotDiskUsage"],
    )


def check_aws_rds_replication_slot_usage(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        replication_slot_space = section["ReplicationSlotDiskUsage"]

    yield Result(state=State.OK, summary=render.bytes(replication_slot_space))

    if (allocated_storage := section.get("AllocatedStorage")) is None or allocated_storage == 0.0:
        yield Result(state=State.WARN, summary="Cannot calculate usage")
        return

    usage = 100.0 * replication_slot_space / allocated_storage
    yield from check_levels_v1(
        value=usage,
        metric_name="aws_rds_replication_slot_disk_usage",
        levels_upper=params.get("levels"),
        render_func=render.percent,
    )


check_plugin_aws_v2_rds_replication_slot_usage = CheckPlugin(
    name="aws_v2_rds_replication_slot_usage",
    service_name="AWS/RDS Replication Slot Usage",
    check_function=check_aws_rds_replication_slot_usage,
    discovery_function=discover_aws_rds_replication_slot_usage,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_disk_usage",
    sections=["aws_v2_rds"],
)

# .
#   .--connections---------------------------------------------------------.
#   |                                        _   _                         |
#   |         ___ ___  _ __  _ __   ___  ___| |_(_) ___  _ __  ___         |
#   |        / __/ _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|        |
#   |       | (_| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \        |
#   |        \___\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_rds_connections(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["DatabaseConnections"],
    )


def check_aws_rds_connections(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        yield from check_levels_v1(
            value=section["DatabaseConnections"],
            metric_name="aws_rds_connections",
            levels_upper=params.get("levels"),
            label="In use",
        )


check_plugin_aws_v2_rds_connections = CheckPlugin(
    name="aws_v2_rds_connections",
    service_name="AWS/RDS Connections",
    sections=["aws_v2_rds"],
    check_function=check_aws_rds_connections,
    discovery_function=discover_aws_rds_connections,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_connections",
)

# .
#   .--replica lag---------------------------------------------------------.
#   |                           _ _             _                          |
#   |            _ __ ___ _ __ | (_) ___ __ _  | | __ _  __ _              |
#   |           | '__/ _ \ '_ \| | |/ __/ _` | | |/ _` |/ _` |             |
#   |           | | |  __/ |_) | | | (_| (_| | | | (_| | (_| |             |
#   |           |_|  \___| .__/|_|_|\___\__,_| |_|\__,_|\__, |             |
#   |                    |_|                            |___/              |
#   '----------------------------------------------------------------------'


def discover_aws_rds_replica_lag(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        ["ReplicaLag"],
    )


def check_aws_rds_replica_lag(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    with _ignore_results_if_missing_data():
        replica_lag = section["ReplicaLag"]

    yield from check_levels_v1(
        value=replica_lag,
        metric_name="aws_rds_replica_lag",
        levels_upper=params.get("lag_levels"),
        render_func=render.timespan,
        label="Lag",
    )

    if (oldest_replica_lag_space := section.get("OldestReplicationSlotLag")) is not None:
        yield from check_levels_v1(
            value=oldest_replica_lag_space,
            metric_name="aws_rds_oldest_replication_slot_lag",
            levels_upper=params.get("slot_levels"),
            render_func=render.bytes,
            label="Oldest replication slot lag",
        )


check_plugin_aws_v2_rds_replica_lag = CheckPlugin(
    name="aws_v2_rds_replica_lag",
    service_name="AWS/RDS Replica Lag",
    check_function=check_aws_rds_replica_lag,
    discovery_function=discover_aws_rds_replica_lag,
    check_default_parameters={},
    check_ruleset_name="aws_v2_rds_replica_lag",
    sections=["aws_v2_rds"],
)
