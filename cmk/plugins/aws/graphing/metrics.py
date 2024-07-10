#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_SECOND = metrics.Unit(metrics.TimeNotation())
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_RCU = metrics.Unit(metrics.DecimalNotation("RCU"))
UNIT_WCU = metrics.Unit(metrics.DecimalNotation("WCU"))

metric_aws_costs_unblended = metrics.Metric(
    name="aws_costs_unblended",
    title=Title("Unblended costs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_total_reservation_utilization = metrics.Metric(
    name="aws_total_reservation_utilization",
    title=Title("Total reservation utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_glacier_number_of_vaults = metrics.Metric(
    name="aws_glacier_number_of_vaults",
    title=Title("Number of vaults"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_glacier_num_archives = metrics.Metric(
    name="aws_glacier_num_archives",
    title=Title("Number of archives"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_glacier_vault_size = metrics.Metric(
    name="aws_glacier_vault_size",
    title=Title("Vault size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

metric_aws_glacier_total_vault_size = metrics.Metric(
    name="aws_glacier_total_vault_size",
    title=Title("Total size of all vaults"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

metric_aws_glacier_largest_vault_size = metrics.Metric(
    name="aws_glacier_largest_vault_size",
    title=Title("Largest vault size"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

metric_aws_num_objects = metrics.Metric(
    name="aws_num_objects",
    title=Title("Number of objects"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_largest_bucket_size = metrics.Metric(
    name="aws_largest_bucket_size",
    title=Title("Largest bucket size"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

metric_aws_surge_queue_length = metrics.Metric(
    name="aws_surge_queue_length",
    title=Title("Surge queue length"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_spillover = metrics.Metric(
    name="aws_spillover",
    title=Title("The rate of requests that were rejected (spillover)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_load_balancer_latency = metrics.Metric(
    name="aws_load_balancer_latency",
    title=Title("Load balancer latency"),
    unit=UNIT_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_http_2xx_rate = metrics.Metric(
    name="aws_http_2xx_rate",
    title=Title("HTTP 2XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)

metric_aws_http_2xx_perc = metrics.Metric(
    name="aws_http_2xx_perc",
    title=Title("Percentage of HTTP 2XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)

metric_aws_http_3xx_rate = metrics.Metric(
    name="aws_http_3xx_rate",
    title=Title("HTTP 3XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_http_3xx_perc = metrics.Metric(
    name="aws_http_3xx_perc",
    title=Title("Percentage of HTTP 3XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_http_4xx_rate = metrics.Metric(
    name="aws_http_4xx_rate",
    title=Title("HTTP 4XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_http_4xx_perc = metrics.Metric(
    name="aws_http_4xx_perc",
    title=Title("Percentage of HTTP 4XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_http_5xx_rate = metrics.Metric(
    name="aws_http_5xx_rate",
    title=Title("HTTP 5XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_http_5xx_perc = metrics.Metric(
    name="aws_http_5xx_perc",
    title=Title("Percentage of HTTP 5XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_http_500_rate = metrics.Metric(
    name="aws_http_500_rate",
    title=Title("HTTP 500 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_http_500_perc = metrics.Metric(
    name="aws_http_500_perc",
    title=Title("Percentage of HTTP 500 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_http_502_rate = metrics.Metric(
    name="aws_http_502_rate",
    title=Title("HTTP 502 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_http_502_perc = metrics.Metric(
    name="aws_http_502_perc",
    title=Title("Percentage of HTTP 502 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

metric_aws_http_503_rate = metrics.Metric(
    name="aws_http_503_rate",
    title=Title("HTTP 503 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_http_503_perc = metrics.Metric(
    name="aws_http_503_perc",
    title=Title("Percentage of HTTP 503 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_http_504_rate = metrics.Metric(
    name="aws_http_504_rate",
    title=Title("HTTP 504 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_http_504_perc = metrics.Metric(
    name="aws_http_504_perc",
    title=Title("Percentage of HTTP 504 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_users_errors_rate = metrics.Metric(
    name="aws_lambda_users_errors_rate",
    title=Title("Lambda user errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_users_errors_perc = metrics.Metric(
    name="aws_lambda_users_errors_perc",
    title=Title("Percentage of Lambda user errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_backend_connection_errors_rate = metrics.Metric(
    name="aws_backend_connection_errors_rate",
    title=Title("Backend connection errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_burst_balance = metrics.Metric(
    name="aws_burst_balance",
    title=Title("Burst balance"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_cpu_credit_balance = metrics.Metric(
    name="aws_cpu_credit_balance",
    title=Title("CPU credit balance"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_rds_bin_log_disk_usage = metrics.Metric(
    name="aws_rds_bin_log_disk_usage",
    title=Title("Bin log disk usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_rds_transaction_logs_disk_usage = metrics.Metric(
    name="aws_rds_transaction_logs_disk_usage",
    title=Title("Transaction logs disk usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_rds_replication_slot_disk_usage = metrics.Metric(
    name="aws_rds_replication_slot_disk_usage",
    title=Title("Replication slot disk usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_rds_replica_lag = metrics.Metric(
    name="aws_rds_replica_lag",
    title=Title("Replica lag"),
    unit=UNIT_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_rds_oldest_replication_slot_lag = metrics.Metric(
    name="aws_rds_oldest_replication_slot_lag",
    title=Title("Oldest replication slot lag size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

metric_aws_rds_connections = metrics.Metric(
    name="aws_rds_connections",
    title=Title("Connections in use"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_request_latency = metrics.Metric(
    name="aws_request_latency",
    title=Title("Request latency"),
    unit=UNIT_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_vpc_elastic_ip_addresses = metrics.Metric(
    name="aws_ec2_vpc_elastic_ip_addresses",
    title=Title("VPC elastic IP addresses"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_elastic_ip_addresses = metrics.Metric(
    name="aws_ec2_elastic_ip_addresses",
    title=Title("Elastic IP addresses"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_spot_inst_requests = metrics.Metric(
    name="aws_ec2_spot_inst_requests",
    title=Title("Spot instance requests"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_ec2_active_spot_fleet_requests = metrics.Metric(
    name="aws_ec2_active_spot_fleet_requests",
    title=Title("Active spot fleet requests"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_spot_fleet_total_target_capacity = metrics.Metric(
    name="aws_ec2_spot_fleet_total_target_capacity",
    title=Title("Spot fleet requests total target capacity"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_total = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_total",
    title=Title("Total running on-demand instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_a1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.2xlarge",
    title=Title("Total running on-demand a1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.4xlarge",
    title=Title("Total running on-demand a1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_a1_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.large",
    title=Title("Total running on-demand a1.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_a1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.medium",
    title=Title("Total running on-demand a1.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_a1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.metal",
    title=Title("Total running on-demand a1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.xlarge",
    title=Title("Total running on-demand a1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c1.medium",
    title=Title("Total running on-demand c1.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c1.xlarge",
    title=Title("Total running on-demand c1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.2xlarge",
    title=Title("Total running on-demand c3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.4xlarge",
    title=Title("Total running on-demand c3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.8xlarge",
    title=Title("Total running on-demand c3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.large",
    title=Title("Total running on-demand c3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.xlarge",
    title=Title("Total running on-demand c3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.2xlarge",
    title=Title("Total running on-demand c4.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.4xlarge",
    title=Title("Total running on-demand c4.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c4_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.8xlarge",
    title=Title("Total running on-demand c4.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.large",
    title=Title("Total running on-demand c4.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.xlarge",
    title=Title("Total running on-demand c4.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.12xlarge",
    title=Title("Total running on-demand c5.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.18xlarge",
    title=Title("Total running on-demand c5.18xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.24xlarge",
    title=Title("Total running on-demand c5.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.2xlarge",
    title=Title("Total running on-demand c5.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.4xlarge",
    title=Title("Total running on-demand c5.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.9xlarge",
    title=Title("Total running on-demand c5.9xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.large",
    title=Title("Total running on-demand c5.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.metal",
    title=Title("Total running on-demand c5.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.xlarge",
    title=Title("Total running on-demand c5.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.12xlarge",
    title=Title("Total running on-demand c5a.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.16xlarge",
    title=Title("Total running on-demand c5a.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.24xlarge",
    title=Title("Total running on-demand c5a.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.2xlarge",
    title=Title("Total running on-demand c5a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.4xlarge",
    title=Title("Total running on-demand c5a.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.8xlarge",
    title=Title("Total running on-demand c5a.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.large",
    title=Title("Total running on-demand c5a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.xlarge",
    title=Title("Total running on-demand c5a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.12xlarge",
    title=Title("Total running on-demand c5ad.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.16xlarge",
    title=Title("Total running on-demand c5ad.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.24xlarge",
    title=Title("Total running on-demand c5ad.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.2xlarge",
    title=Title("Total running on-demand c5ad.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.4xlarge",
    title=Title("Total running on-demand c5ad.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.8xlarge",
    title=Title("Total running on-demand c5ad.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.large",
    title=Title("Total running on-demand c5ad.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.xlarge",
    title=Title("Total running on-demand c5ad.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.12xlarge",
    title=Title("Total running on-demand c5d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.18xlarge",
    title=Title("Total running on-demand c5d.18xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.24xlarge",
    title=Title("Total running on-demand c5d.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.2xlarge",
    title=Title("Total running on-demand c5d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.4xlarge",
    title=Title("Total running on-demand c5d.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.9xlarge",
    title=Title("Total running on-demand c5d.9xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.large",
    title=Title("Total running on-demand c5d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.metal",
    title=Title("Total running on-demand c5d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.xlarge",
    title=Title("Total running on-demand c5d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5n_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.18xlarge",
    title=Title("Total running on-demand c5n.18xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.2xlarge",
    title=Title("Total running on-demand c5n.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.4xlarge",
    title=Title("Total running on-demand c5n.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c5n_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.9xlarge",
    title=Title("Total running on-demand c5n.9xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.large",
    title=Title("Total running on-demand c5n.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.metal",
    title=Title("Total running on-demand c5n.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.xlarge",
    title=Title("Total running on-demand c5n.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.12xlarge",
    title=Title("Total running on-demand c6g.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.16xlarge",
    title=Title("Total running on-demand c6g.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.2xlarge",
    title=Title("Total running on-demand c6g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.4xlarge",
    title=Title("Total running on-demand c6g.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.8xlarge",
    title=Title("Total running on-demand c6g.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.large",
    title=Title("Total running on-demand c6g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.medium",
    title=Title("Total running on-demand c6g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.metal",
    title=Title("Total running on-demand c6g.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.xlarge",
    title=Title("Total running on-demand c6g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.12xlarge",
    title=Title("Total running on-demand c6gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.16xlarge",
    title=Title("Total running on-demand c6gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.2xlarge",
    title=Title("Total running on-demand c6gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.4xlarge",
    title=Title("Total running on-demand c6gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.8xlarge",
    title=Title("Total running on-demand c6gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.large",
    title=Title("Total running on-demand c6gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.medium",
    title=Title("Total running on-demand c6gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.metal",
    title=Title("Total running on-demand c6gd.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.xlarge",
    title=Title("Total running on-demand c6gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.12xlarge",
    title=Title("Total running on-demand c6gn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.16xlarge",
    title=Title("Total running on-demand c6gn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.2xlarge",
    title=Title("Total running on-demand c6gn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.4xlarge",
    title=Title("Total running on-demand c6gn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.8xlarge",
    title=Title("Total running on-demand c6gn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.large",
    title=Title("Total running on-demand c6gn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gn_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.medium",
    title=Title("Total running on-demand c6gn.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.xlarge",
    title=Title("Total running on-demand c6gn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_cc1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cc1.4xlarge",
    title=Title("Total running on-demand cc1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_cc2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cc2.8xlarge",
    title=Title("Total running on-demand cc2.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_cg1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cg1.4xlarge",
    title=Title("Total running on-demand cg1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_cr1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cr1.8xlarge",
    title=Title("Total running on-demand cr1.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.2xlarge",
    title=Title("Total running on-demand d2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_d2_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.4xlarge",
    title=Title("Total running on-demand d2.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.8xlarge",
    title=Title("Total running on-demand d2.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.xlarge",
    title=Title("Total running on-demand d2.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.2xlarge",
    title=Title("Total running on-demand d3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.4xlarge",
    title=Title("Total running on-demand d3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.8xlarge",
    title=Title("Total running on-demand d3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.xlarge",
    title=Title("Total running on-demand d3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_d3en_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.12xlarge",
    title=Title("Total running on-demand d3en.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d3en_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.2xlarge",
    title=Title("Total running on-demand d3en.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3en_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.4xlarge",
    title=Title("Total running on-demand d3en.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3en_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.6xlarge",
    title=Title("Total running on-demand d3en.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3en_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.8xlarge",
    title=Title("Total running on-demand d3en.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3en_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.xlarge",
    title=Title("Total running on-demand d3en.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_f1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f1.16xlarge",
    title=Title("Total running on-demand f1.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_f1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f1.2xlarge",
    title=Title("Total running on-demand f1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_f1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f1.4xlarge",
    title=Title("Total running on-demand f1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g2.2xlarge",
    title=Title("Total running on-demand g2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g2.8xlarge",
    title=Title("Total running on-demand g2.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.16xlarge",
    title=Title("Total running on-demand g3.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.4xlarge",
    title=Title("Total running on-demand g3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.8xlarge",
    title=Title("Total running on-demand g3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g3s_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3s.xlarge",
    title=Title("Total running on-demand g3s.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.16xlarge",
    title=Title("Total running on-demand g4ad.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.2xlarge",
    title=Title("Total running on-demand g4ad.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.4xlarge",
    title=Title("Total running on-demand g4ad.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.8xlarge",
    title=Title("Total running on-demand g4ad.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.xlarge",
    title=Title("Total running on-demand g4ad.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.12xlarge",
    title=Title("Total running on-demand g4dn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g4dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.16xlarge",
    title=Title("Total running on-demand g4dn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.2xlarge",
    title=Title("Total running on-demand g4dn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.4xlarge",
    title=Title("Total running on-demand g4dn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.8xlarge",
    title=Title("Total running on-demand g4dn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.metal",
    title=Title("Total running on-demand g4dn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.xlarge",
    title=Title("Total running on-demand g4dn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.16xlarge",
    title=Title("Total running on-demand h1.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_h1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.2xlarge",
    title=Title("Total running on-demand h1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_h1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.4xlarge",
    title=Title("Total running on-demand h1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.8xlarge",
    title=Title("Total running on-demand h1.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_hi1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_hi1.4xlarge",
    title=Title("Total running on-demand hi1.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_hs1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_hs1.8xlarge",
    title=Title("Total running on-demand hs1.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.2xlarge",
    title=Title("Total running on-demand i2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i2_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.4xlarge",
    title=Title("Total running on-demand i2.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.8xlarge",
    title=Title("Total running on-demand i2.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.xlarge",
    title=Title("Total running on-demand i2.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.16xlarge",
    title=Title("Total running on-demand i3.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.2xlarge",
    title=Title("Total running on-demand i3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.4xlarge",
    title=Title("Total running on-demand i3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.8xlarge",
    title=Title("Total running on-demand i3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.large",
    title=Title("Total running on-demand i3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.metal",
    title=Title("Total running on-demand i3.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.xlarge",
    title=Title("Total running on-demand i3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.12xlarge",
    title=Title("Total running on-demand i3en.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3en_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.24xlarge",
    title=Title("Total running on-demand i3en.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3en_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.2xlarge",
    title=Title("Total running on-demand i3en.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3en_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.3xlarge",
    title=Title("Total running on-demand i3en.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.6xlarge",
    title=Title("Total running on-demand i3en.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3en_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.large",
    title=Title("Total running on-demand i3en.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3en_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.metal",
    title=Title("Total running on-demand i3en.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.xlarge",
    title=Title("Total running on-demand i3en.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_inf1_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.24xlarge",
    title=Title("Total running on-demand inf1.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_inf1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.2xlarge",
    title=Title("Total running on-demand inf1.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_inf1_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.6xlarge",
    title=Title("Total running on-demand inf1.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_inf1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.xlarge",
    title=Title("Total running on-demand inf1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m1_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.large",
    title=Title("Total running on-demand m1.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.medium",
    title=Title("Total running on-demand m1.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m1_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.small",
    title=Title("Total running on-demand m1.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.xlarge",
    title=Title("Total running on-demand m1.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m2.2xlarge",
    title=Title("Total running on-demand m2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m2_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m2.4xlarge",
    title=Title("Total running on-demand m2.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m2.xlarge",
    title=Title("Total running on-demand m2.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.2xlarge",
    title=Title("Total running on-demand m3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.large",
    title=Title("Total running on-demand m3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m3_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.medium",
    title=Title("Total running on-demand m3.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.xlarge",
    title=Title("Total running on-demand m3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m4_10xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.10xlarge",
    title=Title("Total running on-demand m4.10xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m4_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.16xlarge",
    title=Title("Total running on-demand m4.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.2xlarge",
    title=Title("Total running on-demand m4.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.4xlarge",
    title=Title("Total running on-demand m4.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.large",
    title=Title("Total running on-demand m4.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.xlarge",
    title=Title("Total running on-demand m4.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.12xlarge",
    title=Title("Total running on-demand m5.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.16xlarge",
    title=Title("Total running on-demand m5.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.24xlarge",
    title=Title("Total running on-demand m5.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.2xlarge",
    title=Title("Total running on-demand m5.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.4xlarge",
    title=Title("Total running on-demand m5.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.8xlarge",
    title=Title("Total running on-demand m5.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.large",
    title=Title("Total running on-demand m5.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.metal",
    title=Title("Total running on-demand m5.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.xlarge",
    title=Title("Total running on-demand m5.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.12xlarge",
    title=Title("Total running on-demand m5a.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.16xlarge",
    title=Title("Total running on-demand m5a.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.24xlarge",
    title=Title("Total running on-demand m5a.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.2xlarge",
    title=Title("Total running on-demand m5a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.4xlarge",
    title=Title("Total running on-demand m5a.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.8xlarge",
    title=Title("Total running on-demand m5a.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.large",
    title=Title("Total running on-demand m5a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.xlarge",
    title=Title("Total running on-demand m5a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.12xlarge",
    title=Title("Total running on-demand m5ad.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.16xlarge",
    title=Title("Total running on-demand m5ad.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5ad_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.24xlarge",
    title=Title("Total running on-demand m5ad.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.2xlarge",
    title=Title("Total running on-demand m5ad.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.4xlarge",
    title=Title("Total running on-demand m5ad.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.8xlarge",
    title=Title("Total running on-demand m5ad.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5ad_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.large",
    title=Title("Total running on-demand m5ad.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.xlarge",
    title=Title("Total running on-demand m5ad.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.12xlarge",
    title=Title("Total running on-demand m5d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5d_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.16xlarge",
    title=Title("Total running on-demand m5d.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.24xlarge",
    title=Title("Total running on-demand m5d.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.2xlarge",
    title=Title("Total running on-demand m5d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.4xlarge",
    title=Title("Total running on-demand m5d.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5d_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.8xlarge",
    title=Title("Total running on-demand m5d.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.large",
    title=Title("Total running on-demand m5d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.metal",
    title=Title("Total running on-demand m5d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.xlarge",
    title=Title("Total running on-demand m5d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.12xlarge",
    title=Title("Total running on-demand m5dn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.16xlarge",
    title=Title("Total running on-demand m5dn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.24xlarge",
    title=Title("Total running on-demand m5dn.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.2xlarge",
    title=Title("Total running on-demand m5dn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.4xlarge",
    title=Title("Total running on-demand m5dn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.8xlarge",
    title=Title("Total running on-demand m5dn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5dn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.large",
    title=Title("Total running on-demand m5dn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.metal",
    title=Title("Total running on-demand m5dn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.xlarge",
    title=Title("Total running on-demand m5dn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5n_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.12xlarge",
    title=Title("Total running on-demand m5n.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.16xlarge",
    title=Title("Total running on-demand m5n.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.24xlarge",
    title=Title("Total running on-demand m5n.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.2xlarge",
    title=Title("Total running on-demand m5n.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.4xlarge",
    title=Title("Total running on-demand m5n.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5n_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.8xlarge",
    title=Title("Total running on-demand m5n.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.large",
    title=Title("Total running on-demand m5n.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.metal",
    title=Title("Total running on-demand m5n.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.xlarge",
    title=Title("Total running on-demand m5n.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.12xlarge",
    title=Title("Total running on-demand m5zn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.2xlarge",
    title=Title("Total running on-demand m5zn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5zn_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.3xlarge",
    title=Title("Total running on-demand m5zn.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.6xlarge",
    title=Title("Total running on-demand m5zn.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.large",
    title=Title("Total running on-demand m5zn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.metal",
    title=Title("Total running on-demand m5zn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.xlarge",
    title=Title("Total running on-demand m5zn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.12xlarge",
    title=Title("Total running on-demand m6g.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.16xlarge",
    title=Title("Total running on-demand m6g.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.2xlarge",
    title=Title("Total running on-demand m6g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.4xlarge",
    title=Title("Total running on-demand m6g.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.8xlarge",
    title=Title("Total running on-demand m6g.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.large",
    title=Title("Total running on-demand m6g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.medium",
    title=Title("Total running on-demand m6g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.metal",
    title=Title("Total running on-demand m6g.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.xlarge",
    title=Title("Total running on-demand m6g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.12xlarge",
    title=Title("Total running on-demand m6gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.16xlarge",
    title=Title("Total running on-demand m6gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.2xlarge",
    title=Title("Total running on-demand m6gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.4xlarge",
    title=Title("Total running on-demand m6gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.8xlarge",
    title=Title("Total running on-demand m6gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.large",
    title=Title("Total running on-demand m6gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.medium",
    title=Title("Total running on-demand m6gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.metal",
    title=Title("Total running on-demand m6gd.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.xlarge",
    title=Title("Total running on-demand m6gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6i_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.12xlarge",
    title=Title("Total running on-demand m6i.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6i_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.16xlarge",
    title=Title("Total running on-demand m6i.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6i_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.24xlarge",
    title=Title("Total running on-demand m6i.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6i_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.2xlarge",
    title=Title("Total running on-demand m6i.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6i_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.32xlarge",
    title=Title("Total running on-demand m6i.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6i_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.4xlarge",
    title=Title("Total running on-demand m6i.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6i_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.8xlarge",
    title=Title("Total running on-demand m6i.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6i_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.large",
    title=Title("Total running on-demand m6i.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6i_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.xlarge",
    title=Title("Total running on-demand m6i.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_mac1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_mac1.metal",
    title=Title("Total running on-demand mac1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p2_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p2.16xlarge",
    title=Title("Total running on-demand p2.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p2.8xlarge",
    title=Title("Total running on-demand p2.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_p2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p2.xlarge",
    title=Title("Total running on-demand p2.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_p3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3.16xlarge",
    title=Title("Total running on-demand p3.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_p3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3.2xlarge",
    title=Title("Total running on-demand p3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_p3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3.8xlarge",
    title=Title("Total running on-demand p3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_p3dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3dn.24xlarge",
    title=Title("Total running on-demand p3dn.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p4d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p4d.24xlarge",
    title=Title("Total running on-demand p4d.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.2xlarge",
    title=Title("Total running on-demand r3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.4xlarge",
    title=Title("Total running on-demand r3.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.8xlarge",
    title=Title("Total running on-demand r3.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.large",
    title=Title("Total running on-demand r3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.xlarge",
    title=Title("Total running on-demand r3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r4_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.16xlarge",
    title=Title("Total running on-demand r4.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.2xlarge",
    title=Title("Total running on-demand r4.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.4xlarge",
    title=Title("Total running on-demand r4.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r4_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.8xlarge",
    title=Title("Total running on-demand r4.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.large",
    title=Title("Total running on-demand r4.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.xlarge",
    title=Title("Total running on-demand r4.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.12xlarge",
    title=Title("Total running on-demand r5.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.16xlarge",
    title=Title("Total running on-demand r5.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.24xlarge",
    title=Title("Total running on-demand r5.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.2xlarge",
    title=Title("Total running on-demand r5.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.4xlarge",
    title=Title("Total running on-demand r5.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.8xlarge",
    title=Title("Total running on-demand r5.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.large",
    title=Title("Total running on-demand r5.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.metal",
    title=Title("Total running on-demand r5.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.xlarge",
    title=Title("Total running on-demand r5.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.12xlarge",
    title=Title("Total running on-demand r5a.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.16xlarge",
    title=Title("Total running on-demand r5a.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.24xlarge",
    title=Title("Total running on-demand r5a.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.2xlarge",
    title=Title("Total running on-demand r5a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.4xlarge",
    title=Title("Total running on-demand r5a.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.8xlarge",
    title=Title("Total running on-demand r5a.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.large",
    title=Title("Total running on-demand r5a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.xlarge",
    title=Title("Total running on-demand r5a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.12xlarge",
    title=Title("Total running on-demand r5ad.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.16xlarge",
    title=Title("Total running on-demand r5ad.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5ad_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.24xlarge",
    title=Title("Total running on-demand r5ad.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.2xlarge",
    title=Title("Total running on-demand r5ad.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.4xlarge",
    title=Title("Total running on-demand r5ad.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.8xlarge",
    title=Title("Total running on-demand r5ad.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.large",
    title=Title("Total running on-demand r5ad.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.xlarge",
    title=Title("Total running on-demand r5ad.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.12xlarge",
    title=Title("Total running on-demand r5b.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.16xlarge",
    title=Title("Total running on-demand r5b.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5b_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.24xlarge",
    title=Title("Total running on-demand r5b.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5b_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.2xlarge",
    title=Title("Total running on-demand r5b.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5b_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.4xlarge",
    title=Title("Total running on-demand r5b.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.8xlarge",
    title=Title("Total running on-demand r5b.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.large",
    title=Title("Total running on-demand r5b.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.metal",
    title=Title("Total running on-demand r5b.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.xlarge",
    title=Title("Total running on-demand r5b.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.12xlarge",
    title=Title("Total running on-demand r5d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.16xlarge",
    title=Title("Total running on-demand r5d.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.24xlarge",
    title=Title("Total running on-demand r5d.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.2xlarge",
    title=Title("Total running on-demand r5d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.4xlarge",
    title=Title("Total running on-demand r5d.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5d_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.8xlarge",
    title=Title("Total running on-demand r5d.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.large",
    title=Title("Total running on-demand r5d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.metal",
    title=Title("Total running on-demand r5d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.xlarge",
    title=Title("Total running on-demand r5d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.12xlarge",
    title=Title("Total running on-demand r5dn.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.16xlarge",
    title=Title("Total running on-demand r5dn.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.24xlarge",
    title=Title("Total running on-demand r5dn.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.2xlarge",
    title=Title("Total running on-demand r5dn.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.4xlarge",
    title=Title("Total running on-demand r5dn.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.8xlarge",
    title=Title("Total running on-demand r5dn.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5dn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.large",
    title=Title("Total running on-demand r5dn.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.metal",
    title=Title("Total running on-demand r5dn.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.xlarge",
    title=Title("Total running on-demand r5dn.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.12xlarge",
    title=Title("Total running on-demand r5n.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5n_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.16xlarge",
    title=Title("Total running on-demand r5n.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5n_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.24xlarge",
    title=Title("Total running on-demand r5n.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.2xlarge",
    title=Title("Total running on-demand r5n.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.4xlarge",
    title=Title("Total running on-demand r5n.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5n_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.8xlarge",
    title=Title("Total running on-demand r5n.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.large",
    title=Title("Total running on-demand r5n.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.metal",
    title=Title("Total running on-demand r5n.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.xlarge",
    title=Title("Total running on-demand r5n.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.12xlarge",
    title=Title("Total running on-demand r6g.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.16xlarge",
    title=Title("Total running on-demand r6g.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.2xlarge",
    title=Title("Total running on-demand r6g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.4xlarge",
    title=Title("Total running on-demand r6g.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.8xlarge",
    title=Title("Total running on-demand r6g.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.large",
    title=Title("Total running on-demand r6g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.medium",
    title=Title("Total running on-demand r6g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.metal",
    title=Title("Total running on-demand r6g.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.xlarge",
    title=Title("Total running on-demand r6g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.12xlarge",
    title=Title("Total running on-demand r6gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.16xlarge",
    title=Title("Total running on-demand r6gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.2xlarge",
    title=Title("Total running on-demand r6gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.4xlarge",
    title=Title("Total running on-demand r6gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.8xlarge",
    title=Title("Total running on-demand r6gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.large",
    title=Title("Total running on-demand r6gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.medium",
    title=Title("Total running on-demand r6gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.metal",
    title=Title("Total running on-demand r6gd.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.xlarge",
    title=Title("Total running on-demand r6gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t1_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t1.micro",
    title=Title("Total running on-demand t1.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.2xlarge",
    title=Title("Total running on-demand t2.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t2_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.large",
    title=Title("Total running on-demand t2.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t2_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.medium",
    title=Title("Total running on-demand t2.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t2_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.micro",
    title=Title("Total running on-demand t2.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t2_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.nano",
    title=Title("Total running on-demand t2.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t2_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.small",
    title=Title("Total running on-demand t2.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.xlarge",
    title=Title("Total running on-demand t2.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.2xlarge",
    title=Title("Total running on-demand t3.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.large",
    title=Title("Total running on-demand t3.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.medium",
    title=Title("Total running on-demand t3.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.micro",
    title=Title("Total running on-demand t3.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.nano",
    title=Title("Total running on-demand t3.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.small",
    title=Title("Total running on-demand t3.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.xlarge",
    title=Title("Total running on-demand t3.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.2xlarge",
    title=Title("Total running on-demand t3a.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.large",
    title=Title("Total running on-demand t3a.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3a_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.medium",
    title=Title("Total running on-demand t3a.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3a_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.micro",
    title=Title("Total running on-demand t3a.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3a_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.nano",
    title=Title("Total running on-demand t3a.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3a_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.small",
    title=Title("Total running on-demand t3a.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.xlarge",
    title=Title("Total running on-demand t3a.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.2xlarge",
    title=Title("Total running on-demand t4g.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t4g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.large",
    title=Title("Total running on-demand t4g.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t4g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.medium",
    title=Title("Total running on-demand t4g.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t4g_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.micro",
    title=Title("Total running on-demand t4g.micro instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t4g_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.nano",
    title=Title("Total running on-demand t4g.nano instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t4g_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.small",
    title=Title("Total running on-demand t4g.small instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.xlarge",
    title=Title("Total running on-demand t4g.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_12tb1_112xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-12tb1.112xlarge",
    title=Title("Total running on-demand u-12tb1.112xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_12tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-12tb1.metal",
    title=Title("Total running on-demand u-12tb1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_u_18tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-18tb1.metal",
    title=Title("Total running on-demand u-18tb1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_u_24tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-24tb1.metal",
    title=Title("Total running on-demand u-24tb1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_112xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-6tb1.112xlarge",
    title=Title("Total running on-demand u-6tb1.112xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_56xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-6tb1.56xlarge",
    title=Title("Total running on-demand u-6tb1.56xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-6tb1.metal",
    title=Title("Total running on-demand u-6tb1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_9tb1_112xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-9tb1.112xlarge",
    title=Title("Total running on-demand u-9tb1.112xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_9tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-9tb1.metal",
    title=Title("Total running on-demand u-9tb1.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_vt1_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.24xlarge",
    title=Title("Total running on-demand vt1.24xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_vt1_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.3xlarge",
    title=Title("Total running on-demand vt1.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_vt1_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.6xlarge",
    title=Title("Total running on-demand vt1.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1.16xlarge",
    title=Title("Total running on-demand x1.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1.32xlarge",
    title=Title("Total running on-demand x1.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1e_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.16xlarge",
    title=Title("Total running on-demand x1e.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.2xlarge",
    title=Title("Total running on-demand x1e.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x1e_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.32xlarge",
    title=Title("Total running on-demand x1e.32xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x1e_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.4xlarge",
    title=Title("Total running on-demand x1e.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x1e_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.8xlarge",
    title=Title("Total running on-demand x1e.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.xlarge",
    title=Title("Total running on-demand x1e.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.12xlarge",
    title=Title("Total running on-demand x2gd.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.16xlarge",
    title=Title("Total running on-demand x2gd.16xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.2xlarge",
    title=Title("Total running on-demand x2gd.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.4xlarge",
    title=Title("Total running on-demand x2gd.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x2gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.8xlarge",
    title=Title("Total running on-demand x2gd.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.large",
    title=Title("Total running on-demand x2gd.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.medium",
    title=Title("Total running on-demand x2gd.medium instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.metal",
    title=Title("Total running on-demand x2gd.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.xlarge",
    title=Title("Total running on-demand x2gd.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.12xlarge",
    title=Title("Total running on-demand z1d.12xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_z1d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.2xlarge",
    title=Title("Total running on-demand z1d.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_z1d_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.3xlarge",
    title=Title("Total running on-demand z1d.3xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_z1d_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.6xlarge",
    title=Title("Total running on-demand z1d.6xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.large",
    title=Title("Total running on-demand z1d.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.metal",
    title=Title("Total running on-demand z1d.metal instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.xlarge",
    title=Title("Total running on-demand z1d.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_f_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f_vcpu",
    title=Title("Total running on-demand F instances vCPUs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g_vcpu",
    title=Title("Total running on-demand G instances vCPUs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i_vcpu",
    title=Title("Total running on-demand Inf instances vCPUs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_p_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p_vcpu",
    title=Title("Total running on-demand P instances vCPUs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_x_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x_vcpu",
    title=Title("Total running on-demand X instances vCPUs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances___vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances___vcpu",
    title=Title("Total running on-demand Standard (A, C, D, H, I, M, R, T, Z) instances vCPUs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_consumed_lcus = metrics.Metric(
    name="aws_consumed_lcus",
    title=Title("Consumed load balancer capacity units"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_active_connections = metrics.Metric(
    name="aws_active_connections",
    title=Title("Active connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_active_tls_connections = metrics.Metric(
    name="aws_active_tls_connections",
    title=Title("Active TLS connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_new_connections = metrics.Metric(
    name="aws_new_connections",
    title=Title("New connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_new_tls_connections = metrics.Metric(
    name="aws_new_tls_connections",
    title=Title("New TLS connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_rejected_connections = metrics.Metric(
    name="aws_rejected_connections",
    title=Title("Rejected connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_client_tls_errors = metrics.Metric(
    name="aws_client_tls_errors",
    title=Title("Client TLS errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_http_redirects = metrics.Metric(
    name="aws_http_redirects",
    title=Title("HTTP redirects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_http_redirect_url_limit = metrics.Metric(
    name="aws_http_redirect_url_limit",
    title=Title("HTTP redirects URL limit exceeded"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_http_fixed_response = metrics.Metric(
    name="aws_http_fixed_response",
    title=Title("HTTP fixed responses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_proc_bytes = metrics.Metric(
    name="aws_proc_bytes",
    title=Title("Processed bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_proc_bytes_tls = metrics.Metric(
    name="aws_proc_bytes_tls",
    title=Title("TLS processed bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_ipv6_proc_bytes = metrics.Metric(
    name="aws_ipv6_proc_bytes",
    title=Title("IPv6 processed bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ipv6_requests = metrics.Metric(
    name="aws_ipv6_requests",
    title=Title("IPv6 requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_rule_evaluations = metrics.Metric(
    name="aws_rule_evaluations",
    title=Title("Rule evaluations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_failed_tls_client_handshake = metrics.Metric(
    name="aws_failed_tls_client_handshake",
    title=Title("Failed TLS client handshake"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_failed_tls_target_handshake = metrics.Metric(
    name="aws_failed_tls_target_handshake",
    title=Title("Failed TLS target handshake"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_tcp_client_rst = metrics.Metric(
    name="aws_tcp_client_rst",
    title=Title("TCP client resets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_tcp_elb_rst = metrics.Metric(
    name="aws_tcp_elb_rst",
    title=Title("TCP ELB resets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_tcp_target_rst = metrics.Metric(
    name="aws_tcp_target_rst",
    title=Title("TCP target resets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_s3_downloads = metrics.Metric(
    name="aws_s3_downloads",
    title=Title("Download"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_s3_uploads = metrics.Metric(
    name="aws_s3_uploads",
    title=Title("Upload"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_s3_select_object_scanned = metrics.Metric(
    name="aws_s3_select_object_scanned",
    title=Title("SELECT object scanned"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_s3_select_object_returned = metrics.Metric(
    name="aws_s3_select_object_returned",
    title=Title("SELECT object returned"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_elb_load_balancers = metrics.Metric(
    name="aws_elb_load_balancers",
    title=Title("Load balancers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_elb_load_balancer_listeners = metrics.Metric(
    name="aws_elb_load_balancer_listeners",
    title=Title("Load balancer listeners"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_elb_load_balancer_registered_instances = metrics.Metric(
    name="aws_elb_load_balancer_registered_instances",
    title=Title("Load balancer registered instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_rds_db_clusters = metrics.Metric(
    name="aws_rds_db_clusters",
    title=Title("DB clusters"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_rds_db_cluster_parameter_groups = metrics.Metric(
    name="aws_rds_db_cluster_parameter_groups",
    title=Title("DB cluster parameter groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_rds_db_instances = metrics.Metric(
    name="aws_rds_db_instances",
    title=Title("DB instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_rds_event_subscriptions = metrics.Metric(
    name="aws_rds_event_subscriptions",
    title=Title("Event subscriptions"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_rds_manual_snapshots = metrics.Metric(
    name="aws_rds_manual_snapshots",
    title=Title("Manual snapshots"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_rds_option_groups = metrics.Metric(
    name="aws_rds_option_groups",
    title=Title("Option groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_rds_db_parameter_groups = metrics.Metric(
    name="aws_rds_db_parameter_groups",
    title=Title("DB parameter groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_rds_read_replica_per_master = metrics.Metric(
    name="aws_rds_read_replica_per_master",
    title=Title("Read replica per master"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_rds_reserved_db_instances = metrics.Metric(
    name="aws_rds_reserved_db_instances",
    title=Title("Reserved DB instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_rds_db_security_groups = metrics.Metric(
    name="aws_rds_db_security_groups",
    title=Title("DB security groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_rds_db_subnet_groups = metrics.Metric(
    name="aws_rds_db_subnet_groups",
    title=Title("DB subnet groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_rds_subnet_per_db_subnet_groups = metrics.Metric(
    name="aws_rds_subnet_per_db_subnet_groups",
    title=Title("Subnet per DB subnet groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_rds_allocated_storage = metrics.Metric(
    name="aws_rds_allocated_storage",
    title=Title("Allocated storage"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_rds_auths_per_db_security_groups = metrics.Metric(
    name="aws_rds_auths_per_db_security_groups",
    title=Title("Authorizations per DB security group"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_rds_db_cluster_roles = metrics.Metric(
    name="aws_rds_db_cluster_roles",
    title=Title("DB cluster roles"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ebs_block_store_snapshots = metrics.Metric(
    name="aws_ebs_block_store_snapshots",
    title=Title("Block store snapshots"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_ebs_block_store_space_standard = metrics.Metric(
    name="aws_ebs_block_store_space_standard",
    title=Title("Magnetic volumes space"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

metric_aws_ebs_block_store_space_io1 = metrics.Metric(
    name="aws_ebs_block_store_space_io1",
    title=Title("Provisioned IOPS SSD (io1) space"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ebs_block_store_iops_io1 = metrics.Metric(
    name="aws_ebs_block_store_iops_io1",
    title=Title("Provisioned IOPS SSD (io1) IO operations per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_ebs_block_store_space_io2 = metrics.Metric(
    name="aws_ebs_block_store_space_io2",
    title=Title("Provisioned IOPS SSD (io2) space"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

metric_aws_ebs_block_store_iops_io2 = metrics.Metric(
    name="aws_ebs_block_store_iops_io2",
    title=Title("Provisioned IOPS SSD (io2) IO operations per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_aws_ebs_block_store_space_gp2 = metrics.Metric(
    name="aws_ebs_block_store_space_gp2",
    title=Title("General purpose SSD (gp2) space"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

metric_aws_ebs_block_store_space_gp3 = metrics.Metric(
    name="aws_ebs_block_store_space_gp3",
    title=Title("General purpose SSD (gp3) space"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

metric_aws_ebs_block_store_space_sc1 = metrics.Metric(
    name="aws_ebs_block_store_space_sc1",
    title=Title("Cold HDD space"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

metric_aws_ebs_block_store_space_st1 = metrics.Metric(
    name="aws_ebs_block_store_space_st1",
    title=Title("Throughput optimized HDD space"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

metric_aws_elbv2_application_load_balancers = metrics.Metric(
    name="aws_elbv2_application_load_balancers",
    title=Title("Application load balancers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_elbv2_application_load_balancer_rules = metrics.Metric(
    name="aws_elbv2_application_load_balancer_rules",
    title=Title("Application load balancer rules"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_elbv2_application_load_balancer_listeners = metrics.Metric(
    name="aws_elbv2_application_load_balancer_listeners",
    title=Title("Application load balancer listeners"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_elbv2_application_load_balancer_target_groups = metrics.Metric(
    name="aws_elbv2_application_load_balancer_target_groups",
    title=Title("Application load balancer target groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_elbv2_application_load_balancer_certificates = metrics.Metric(
    name="aws_elbv2_application_load_balancer_certificates",
    title=Title("Application load balancer certificates"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_elbv2_network_load_balancers = metrics.Metric(
    name="aws_elbv2_network_load_balancers",
    title=Title("Network load balancers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_elbv2_network_load_balancer_listeners = metrics.Metric(
    name="aws_elbv2_network_load_balancer_listeners",
    title=Title("Network load balancer listeners"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_elbv2_network_load_balancer_target_groups = metrics.Metric(
    name="aws_elbv2_network_load_balancer_target_groups",
    title=Title("Network load balancer target groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_elbv2_load_balancer_target_groups = metrics.Metric(
    name="aws_elbv2_load_balancer_target_groups",
    title=Title("Load balancers target groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_number_of_tables = metrics.Metric(
    name="aws_dynamodb_number_of_tables",
    title=Title("Number of tables"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_dynamodb_read_capacity = metrics.Metric(
    name="aws_dynamodb_read_capacity",
    title=Title("Read capacity"),
    unit=UNIT_RCU,
    color=metrics.Color.ORANGE,
)

metric_aws_dynamodb_write_capacity = metrics.Metric(
    name="aws_dynamodb_write_capacity",
    title=Title("Write capacity"),
    unit=UNIT_WCU,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_consumed_rcu",
    title=Title("Average consumption"),
    unit=UNIT_RCU,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_rcu_perc = metrics.Metric(
    name="aws_dynamodb_consumed_rcu_perc",
    title=Title("Average usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_wcu = metrics.Metric(
    name="aws_dynamodb_consumed_wcu",
    title=Title("Average consumption"),
    unit=UNIT_WCU,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_wcu_perc = metrics.Metric(
    name="aws_dynamodb_consumed_wcu_perc",
    title=Title("Average usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_minimum_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_minimum_consumed_rcu",
    title=Title("Minimum single-request consumption"),
    unit=UNIT_RCU,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_maximum_consumed_rcu",
    title=Title("Maximum single-request consumption"),
    unit=UNIT_RCU,
    color=metrics.Color.ORANGE,
)

metric_aws_dynamodb_minimum_consumed_wcu = metrics.Metric(
    name="aws_dynamodb_minimum_consumed_wcu",
    title=Title("Minimum single-request consumption"),
    unit=UNIT_WCU,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_wcu = metrics.Metric(
    name="aws_dynamodb_maximum_consumed_wcu",
    title=Title("Maximum single-request consumption"),
    unit=UNIT_WCU,
    color=metrics.Color.ORANGE,
)

metric_aws_dynamodb_query_average_latency = metrics.Metric(
    name="aws_dynamodb_query_average_latency",
    title=Title("Average latency of successful query requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_query_maximum_latency = metrics.Metric(
    name="aws_dynamodb_query_maximum_latency",
    title=Title("Maximum latency of successful query requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_dynamodb_getitem_average_latency = metrics.Metric(
    name="aws_dynamodb_getitem_average_latency",
    title=Title("Average latency of successful GetItem requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_getitem_maximum_latency = metrics.Metric(
    name="aws_dynamodb_getitem_maximum_latency",
    title=Title("Maximum latency of successful GetItem requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_dynamodb_putitem_average_latency = metrics.Metric(
    name="aws_dynamodb_putitem_average_latency",
    title=Title("Average latency of successful PutItem requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_putitem_maximum_latency = metrics.Metric(
    name="aws_dynamodb_putitem_maximum_latency",
    title=Title("Maximum latency of successful PutItem requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_wafv2_web_acls = metrics.Metric(
    name="aws_wafv2_web_acls",
    title=Title("Number of web ACLs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_wafv2_rule_groups = metrics.Metric(
    name="aws_wafv2_rule_groups",
    title=Title("Number of rule groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_wafv2_ip_sets = metrics.Metric(
    name="aws_wafv2_ip_sets",
    title=Title("Number of IP sets"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_wafv2_regex_pattern_sets = metrics.Metric(
    name="aws_wafv2_regex_pattern_sets",
    title=Title("Number of regex sets"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_wafv2_web_acl_capacity_units = metrics.Metric(
    name="aws_wafv2_web_acl_capacity_units",
    title=Title("Web ACL capacity units (WCUs)"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_wafv2_requests_rate = metrics.Metric(
    name="aws_wafv2_requests_rate",
    title=Title("Avg. request rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)

metric_aws_wafv2_allowed_requests_rate = metrics.Metric(
    name="aws_wafv2_allowed_requests_rate",
    title=Title("Avg. rate of allowed requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_rate = metrics.Metric(
    name="aws_wafv2_blocked_requests_rate",
    title=Title("Avg. rate of blocked requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_wafv2_allowed_requests_perc = metrics.Metric(
    name="aws_wafv2_allowed_requests_perc",
    title=Title("Percentage of allowed requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_perc = metrics.Metric(
    name="aws_wafv2_blocked_requests_perc",
    title=Title("Percentage of blocked requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

metric_aws_cloudwatch_alarms_cloudwatch_alarms = metrics.Metric(
    name="aws_cloudwatch_alarms_cloudwatch_alarms",
    title=Title("CloudWatch alarms"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_duration = metrics.Metric(
    name="aws_lambda_duration",
    title=Title("Duration of Lambda functions"),
    unit=UNIT_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_lambda_duration_in_percent = metrics.Metric(
    name="aws_lambda_duration_in_percent",
    title=Title("Duration in percent of Lambda timeout"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

metric_aws_lambda_invocations = metrics.Metric(
    name="aws_lambda_invocations",
    title=Title("Invocations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_lambda_throttles = metrics.Metric(
    name="aws_lambda_throttles",
    title=Title("Throttles"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_lambda_iterator_age = metrics.Metric(
    name="aws_lambda_iterator_age",
    title=Title("Iterator age"),
    unit=UNIT_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_lambda_dead_letter_errors = metrics.Metric(
    name="aws_lambda_dead_letter_errors",
    title=Title("Dead letter errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_init_duration_absolute = metrics.Metric(
    name="aws_lambda_init_duration_absolute",
    title=Title("Init duration"),
    unit=UNIT_SECOND,
    color=metrics.Color.BLUE,
)

metric_aws_lambda_cold_starts_in_percent = metrics.Metric(
    name="aws_lambda_cold_starts_in_percent",
    title=Title("Cold starts in percent"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_lambda_concurrent_executions_in_percent = metrics.Metric(
    name="aws_lambda_concurrent_executions_in_percent",
    title=Title("Concurrent executions in percent"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_concurrent_executions = metrics.Metric(
    name="aws_lambda_concurrent_executions",
    title=Title("Concurrent executions"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_unreserved_concurrent_executions_in_percent = metrics.Metric(
    name="aws_lambda_unreserved_concurrent_executions_in_percent",
    title=Title("Unreserved concurrent executions in percent"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_lambda_unreserved_concurrent_executions = metrics.Metric(
    name="aws_lambda_unreserved_concurrent_executions",
    title=Title("Unreserved concurrent executions"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_lambda_provisioned_concurrency_executions = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_executions",
    title=Title("Provisioned concurrency executions"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_aws_lambda_provisioned_concurrency_invocations = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_invocations",
    title=Title("Provisioned concurrency invocations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_lambda_provisioned_concurrency_spillover_invocations = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_spillover_invocations",
    title=Title("Provisioned concurrency spillover invocations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_lambda_provisioned_concurrency_utilization = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_utilization",
    title=Title("Provisioned concurrency utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_lambda_code_size_in_percent = metrics.Metric(
    name="aws_lambda_code_size_in_percent",
    title=Title("Code size in percent"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_code_size_absolute = metrics.Metric(
    name="aws_lambda_code_size_absolute",
    title=Title("Code size"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_lambda_memory_size_in_percent = metrics.Metric(
    name="aws_lambda_memory_size_in_percent",
    title=Title("Memory size in percent"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

metric_aws_lambda_memory_size_absolute = metrics.Metric(
    name="aws_lambda_memory_size_absolute",
    title=Title("Memory size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

metric_aws_route53_child_health_check_healthy_count = metrics.Metric(
    name="aws_route53_child_health_check_healthy_count",
    title=Title("Health check healty count"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_route53_connection_time = metrics.Metric(
    name="aws_route53_connection_time",
    title=Title("Connection time"),
    unit=UNIT_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_route53_health_check_percentage_healthy = metrics.Metric(
    name="aws_route53_health_check_percentage_healthy",
    title=Title("Health check percentage healty"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_route53_ssl_handshake_time = metrics.Metric(
    name="aws_route53_ssl_handshake_time",
    title=Title("SSL handshake time"),
    unit=UNIT_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_route53_time_to_first_byte = metrics.Metric(
    name="aws_route53_time_to_first_byte",
    title=Title("Time to first byte"),
    unit=UNIT_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_sns_topics_standard = metrics.Metric(
    name="aws_sns_topics_standard",
    title=Title("Standard topics"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_sns_topics_fifo = metrics.Metric(
    name="aws_sns_topics_fifo",
    title=Title("FIFO topics"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_cloudfront_requests = metrics.Metric(
    name="aws_cloudfront_requests",
    title=Title("Requests"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_aws_cloudfront_total_error_rate = metrics.Metric(
    name="aws_cloudfront_total_error_rate",
    title=Title("Total error rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

metric_aws_cloudfront_4xx_error_rate = metrics.Metric(
    name="aws_cloudfront_4xx_error_rate",
    title=Title("4xx error rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_cloudfront_5xx_error_rate = metrics.Metric(
    name="aws_cloudfront_5xx_error_rate",
    title=Title("5xx error rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ecs_clusters = metrics.Metric(
    name="aws_ecs_clusters",
    title=Title("Clusters"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_elasticache_nodes = metrics.Metric(
    name="aws_elasticache_nodes",
    title=Title("Nodes"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_aws_elasticache_parameter_groups = metrics.Metric(
    name="aws_elasticache_parameter_groups",
    title=Title("Parameter groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_elasticache_subnet_groups = metrics.Metric(
    name="aws_elasticache_subnet_groups",
    title=Title("Subnet groups"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)
