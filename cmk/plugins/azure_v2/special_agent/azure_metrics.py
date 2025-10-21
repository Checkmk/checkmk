# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

type Intervals = Literal["PT1M", "PT5M", "PT1H"]
type Aggregations = Literal["average", "minimum", "maximum", "total", "count"]


@dataclass(frozen=True, kw_only=True)
class DimensionFilter:
    name: str
    value: str


@dataclass(frozen=True, kw_only=True)
class AzureMetric:
    name: str
    interval: Intervals
    aggregation: Aggregations
    dimension_filter: DimensionFilter | None = None


storage_percent = AzureMetric(name="storage_percent", interval="PT1M", aggregation="average")
cpu_percent = AzureMetric(name="cpu_percent", interval="PT1M", aggregation="average")
memory_percent = AzureMetric(name="memory_percent", interval="PT1M", aggregation="average")
io_consumption_percent = AzureMetric(
    name="io_consumption_percent", interval="PT1M", aggregation="average"
)
serverlog_storage_percent = AzureMetric(
    name="serverlog_storage_percent", interval="PT1M", aggregation="average"
)
active_connections = AzureMetric(name="active_connections", interval="PT1M", aggregation="average")
connections_failed = AzureMetric(name="connections_failed", interval="PT1M", aggregation="total")
network_bytes_ingress = AzureMetric(
    name="network_bytes_ingress", interval="PT1M", aggregation="total"
)
network_bytes_egress = AzureMetric(
    name="network_bytes_egress", interval="PT1M", aggregation="total"
)

database_accounts_metrics = [
    AzureMetric(name="ServiceAvailability", interval="PT1H", aggregation="minimum"),
    AzureMetric(name="TotalRequests", interval="PT1M", aggregation="count"),
    AzureMetric(
        name="TotalRequests",
        interval="PT1M",
        aggregation="count",
        dimension_filter=DimensionFilter(
            name="StatusCode",
            value="429",
        ),
    ),
    AzureMetric(
        name="TotalRequests",
        interval="PT1M",
        aggregation="count",
        dimension_filter=DimensionFilter(
            name="StatusCode",
            value="404",
        ),
    ),
    AzureMetric(name="TotalRequestUnitsPreview", interval="PT1M", aggregation="total"),
    AzureMetric(name="NormalizedRUConsumption", interval="PT1M", aggregation="maximum"),
]

ALL_METRICS: dict[str, list[AzureMetric]] = {
    # to add a new metric, just add a made up name, run the
    # agent, and you'll get a error listing available metrics!
    # key: list of (name(s), interval, aggregation, filter)
    # Also remember to add the service to the WATO rule:
    # cmk/gui/plugins/wato/special_agents/azure.py
    "Microsoft.Network/virtualNetworkGateways": [
        AzureMetric(name="AverageBandwidth", interval="PT5M", aggregation="average"),
        AzureMetric(name="P2SBandwidth", interval="PT5M", aggregation="average"),
        AzureMetric(name="TunnelIngressBytes", interval="PT5M", aggregation="count"),
        AzureMetric(name="TunnelEgressBytes", interval="PT5M", aggregation="count"),
        AzureMetric(name="TunnelIngressPacketDropCount", interval="PT5M", aggregation="count"),
        AzureMetric(name="TunnelEgressPacketDropCount", interval="PT5M", aggregation="count"),
        AzureMetric(name="P2SConnectionCount", interval="PT1M", aggregation="maximum"),
    ],
    "Microsoft.Sql/servers/databases": [
        storage_percent,
        AzureMetric(name="deadlock", interval="PT1M", aggregation="average"),
        cpu_percent,
        AzureMetric(name="dtu_consumption_percent", interval="PT1M", aggregation="average"),
        AzureMetric(name="connection_successful", interval="PT1M", aggregation="average"),
        AzureMetric(name="connection_failed", interval="PT1M", aggregation="average"),
    ],
    "Microsoft.Storage/storageAccounts": [
        AzureMetric(name="UsedCapacity", interval="PT1H", aggregation="total"),
        AzureMetric(name="Ingress", interval="PT1H", aggregation="total"),
        AzureMetric(name="Egress", interval="PT1H", aggregation="total"),
        AzureMetric(name="Transactions", interval="PT1H", aggregation="total"),
        AzureMetric(name="SuccessServerLatency", interval="PT1H", aggregation="average"),
        AzureMetric(name="SuccessE2ELatency", interval="PT1H", aggregation="average"),
        AzureMetric(name="Availability", interval="PT1H", aggregation="average"),
    ],
    "Microsoft.Web/sites": [
        AzureMetric(name="CpuTime", interval="PT1M", aggregation="total"),
        AzureMetric(name="AverageResponseTime", interval="PT1M", aggregation="total"),
        AzureMetric(name="Http5xx", interval="PT1M", aggregation="total"),
    ],
    "Microsoft.DBforMySQL/servers": [
        cpu_percent,
        memory_percent,
        io_consumption_percent,
        serverlog_storage_percent,
        storage_percent,
        active_connections,
        connections_failed,
        network_bytes_ingress,
        network_bytes_egress,
        AzureMetric(name="seconds_behind_master", interval="PT1M", aggregation="maximum"),
    ],
    "Microsoft.DBforMySQL/flexibleServers": [
        cpu_percent,
        memory_percent,
        io_consumption_percent,
        serverlog_storage_percent,
        storage_percent,
        active_connections,
        AzureMetric(name="aborted_connections", interval="PT1M", aggregation="total"),
        network_bytes_ingress,
        network_bytes_egress,
        AzureMetric(name="replication_lag", interval="PT1M", aggregation="maximum"),
    ],
    "Microsoft.DBforPostgreSQL/servers": [
        cpu_percent,
        memory_percent,
        io_consumption_percent,
        serverlog_storage_percent,
        storage_percent,
        active_connections,
        connections_failed,
        network_bytes_ingress,
        network_bytes_egress,
        AzureMetric(name="pg_replica_log_delay_in_seconds", interval="PT1M", aggregation="maximum"),
    ],
    "Microsoft.DBforPostgreSQL/flexibleServers": [
        cpu_percent,
        memory_percent,
        AzureMetric(name="disk_iops_consumed_percentage", interval="PT1M", aggregation="average"),
        storage_percent,
        active_connections,
        connections_failed,
        network_bytes_ingress,
        network_bytes_egress,
        AzureMetric(
            name="physical_replication_delay_in_seconds", interval="PT1M", aggregation="maximum"
        ),
    ],
    "Microsoft.Network/trafficmanagerprofiles": [
        AzureMetric(name="QpsByEndpoint", interval="PT1M", aggregation="total"),
        AzureMetric(
            name="ProbeAgentCurrentEndpointStateByProfileResourceId",
            interval="PT1M",
            aggregation="maximum",
        ),
    ],
    "Microsoft.Network/loadBalancers": [
        AzureMetric(name="ByteCount", interval="PT1M", aggregation="total"),
        AzureMetric(name="AllocatedSnatPorts", interval="PT1M", aggregation="average"),
        AzureMetric(name="UsedSnatPorts", interval="PT1M", aggregation="average"),
        AzureMetric(name="VipAvailability", interval="PT1M", aggregation="average"),
        AzureMetric(name="DipAvailability", interval="PT1M", aggregation="average"),
    ],
    "Microsoft.Network/applicationGateways": [
        AzureMetric(name="HealthyHostCount", interval="PT1M", aggregation="average"),
        AzureMetric(name="FailedRequests", interval="PT1M", aggregation="count"),
    ],
    "Microsoft.Compute/virtualMachines": [
        AzureMetric(name="Percentage CPU", interval="PT1M", aggregation="average"),
        AzureMetric(name="CPU Credits Consumed", interval="PT1M", aggregation="average"),
        AzureMetric(name="CPU Credits Remaining", interval="PT1M", aggregation="average"),
        AzureMetric(name="Available Memory Bytes", interval="PT1M", aggregation="average"),
        AzureMetric(name="Disk Read Operations/Sec", interval="PT1M", aggregation="average"),
        AzureMetric(name="Disk Write Operations/Sec", interval="PT1M", aggregation="average"),
        AzureMetric(name="Network In Total", interval="PT1M", aggregation="total"),
        AzureMetric(name="Network Out Total", interval="PT1M", aggregation="total"),
        AzureMetric(name="Disk Read Bytes", interval="PT1M", aggregation="total"),
        AzureMetric(name="Disk Write Bytes", interval="PT1M", aggregation="total"),
    ],
    "Microsoft.Cache/Redis": [
        AzureMetric(name="allconnectedclients", interval="PT1M", aggregation="maximum"),
        AzureMetric(name="allConnectionsCreatedPerSecond", interval="PT1M", aggregation="maximum"),
        AzureMetric(name="allConnectionsClosedPerSecond", interval="PT1M", aggregation="maximum"),
        AzureMetric(name="allpercentprocessortime", interval="PT1M", aggregation="maximum"),
        AzureMetric(name="allcachehits", interval="PT1M", aggregation="total"),
        AzureMetric(name="allcachemisses", interval="PT1M", aggregation="total"),
        AzureMetric(name="cachemissrate", interval="PT1M", aggregation="total"),
        AzureMetric(name="allgetcommands", interval="PT1M", aggregation="total"),
        AzureMetric(name="allusedmemory", interval="PT1M", aggregation="total"),
        AzureMetric(name="allusedmemorypercentage", interval="PT1M", aggregation="total"),
        AzureMetric(name="allusedmemoryRss", interval="PT1M", aggregation="total"),
        AzureMetric(name="allevictedkeys", interval="PT1M", aggregation="total"),
        AzureMetric(name="allexpiredkeys", interval="PT1M", aggregation="total"),
        AzureMetric(name="LatencyP99", interval="PT1M", aggregation="average"),
        AzureMetric(name="cacheLatency", interval="PT1M", aggregation="average"),
        AzureMetric(name="GeoReplicationHealthy", interval="PT1M", aggregation="minimum"),
        AzureMetric(name="GeoReplicationConnectivityLag", interval="PT1M", aggregation="average"),
        AzureMetric(name="allcacheRead", interval="PT1M", aggregation="maximum"),
        AzureMetric(name="allcacheWrite", interval="PT1M", aggregation="maximum"),
    ],
    "Microsoft.Network/natGateways": [
        AzureMetric(name="DatapathAvailability", interval="PT1M", aggregation="average"),
    ],
    "Microsoft.DocumentDb/databaseAccounts": database_accounts_metrics,
    "Microsoft.DocumentDB/databaseAccounts": database_accounts_metrics,
}

OPTIONAL_METRICS: Mapping[str, Sequence[str]] = {
    "Microsoft.Sql/servers/databases": [
        "storage_percent",
        "deadlock",
        "dtu_consumption_percent",
    ],
    "Microsoft.DBforMySQL/servers": ["seconds_behind_master"],
    "Microsoft.DBforMySQL/flexibleServers": ["replication_lag"],
    "Microsoft.DBforPostgreSQL/servers": ["pg_replica_log_delay_in_seconds"],
    "Microsoft.DBforPostgreSQL/flexibleServers": ["physical_replication_delay_in_seconds"],
    "Microsoft.Network/loadBalancers": ["AllocatedSnatPorts", "UsedSnatPorts"],
    "Microsoft.Compute/virtualMachines": [
        "CPU Credits Consumed",
        "CPU Credits Remaining",
    ],
}
