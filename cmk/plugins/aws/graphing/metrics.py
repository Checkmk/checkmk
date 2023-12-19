#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, Localizable, metrics, Unit

metric_aws_costs_unblended = metrics.Metric(
    name="aws_costs_unblended",
    title=Localizable("Unblended costs"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_glacier_number_of_vaults = metrics.Metric(
    name="aws_glacier_number_of_vaults",
    title=Localizable("Number of vaults"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_glacier_num_archives = metrics.Metric(
    name="aws_glacier_num_archives",
    title=Localizable("Number of archives"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_glacier_vault_size = metrics.Metric(
    name="aws_glacier_vault_size",
    title=Localizable("Vault size"),
    unit=Unit.BYTES_IEC,
    color=Color.ORANGE,
)

metric_aws_glacier_total_vault_size = metrics.Metric(
    name="aws_glacier_total_vault_size",
    title=Localizable("Total size of all vaults"),
    unit=Unit.BYTES_IEC,
    color=Color.ORANGE,
)

metric_aws_glacier_largest_vault_size = metrics.Metric(
    name="aws_glacier_largest_vault_size",
    title=Localizable("Largest vault size"),
    unit=Unit.BYTES_IEC,
    color=Color.YELLOW,
)

metric_aws_num_objects = metrics.Metric(
    name="aws_num_objects",
    title=Localizable("Number of objects"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_bucket_size = metrics.Metric(
    name="aws_bucket_size",
    title=Localizable("Bucket size"),
    unit=Unit.BYTES_IEC,
    color=Color.ORANGE,
)

metric_aws_largest_bucket_size = metrics.Metric(
    name="aws_largest_bucket_size",
    title=Localizable("Largest bucket size"),
    unit=Unit.BYTES_IEC,
    color=Color.YELLOW,
)

metric_aws_surge_queue_length = metrics.Metric(
    name="aws_surge_queue_length",
    title=Localizable("Surge queue length"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_spillover = metrics.Metric(
    name="aws_spillover",
    title=Localizable("The rate of requests that were rejected (spillover)"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_PURPLE,
)

metric_aws_load_balancer_latency = metrics.Metric(
    name="aws_load_balancer_latency",
    title=Localizable("Load balancer latency"),
    unit=Unit.SECOND,
    color=Color.YELLOW,
)

metric_aws_http_2xx_rate = metrics.Metric(
    name="aws_http_2xx_rate",
    title=Localizable("HTTP 2XX errors"),
    unit=Unit.PER_SECOND,
    color=Color.BROWN,
)

metric_aws_http_2xx_perc = metrics.Metric(
    name="aws_http_2xx_perc",
    title=Localizable("Percentage of HTTP 2XX errors"),
    unit=Unit.PERCENTAGE,
    color=Color.BROWN,
)

metric_aws_http_3xx_rate = metrics.Metric(
    name="aws_http_3xx_rate",
    title=Localizable("HTTP 3XX errors"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_http_3xx_perc = metrics.Metric(
    name="aws_http_3xx_perc",
    title=Localizable("Percentage of HTTP 3XX errors"),
    unit=Unit.PERCENTAGE,
    color=Color.PURPLE,
)

metric_aws_http_4xx_rate = metrics.Metric(
    name="aws_http_4xx_rate",
    title=Localizable("HTTP 4XX errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_GREEN,
)

metric_aws_http_4xx_perc = metrics.Metric(
    name="aws_http_4xx_perc",
    title=Localizable("Percentage of HTTP 4XX errors"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_GREEN,
)

metric_aws_http_5xx_rate = metrics.Metric(
    name="aws_http_5xx_rate",
    title=Localizable("HTTP 5XX errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_http_5xx_perc = metrics.Metric(
    name="aws_http_5xx_perc",
    title=Localizable("Percentage of HTTP 5XX errors"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_http_500_rate = metrics.Metric(
    name="aws_http_500_rate",
    title=Localizable("HTTP 500 errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_PURPLE,
)

metric_aws_http_500_perc = metrics.Metric(
    name="aws_http_500_perc",
    title=Localizable("Percentage of HTTP 500 errors"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_PURPLE,
)

metric_aws_http_502_rate = metrics.Metric(
    name="aws_http_502_rate",
    title=Localizable("HTTP 502 errors"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_http_502_perc = metrics.Metric(
    name="aws_http_502_perc",
    title=Localizable("Percentage of HTTP 502 errors"),
    unit=Unit.PERCENTAGE,
    color=Color.ORANGE,
)

metric_aws_http_503_rate = metrics.Metric(
    name="aws_http_503_rate",
    title=Localizable("HTTP 503 errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_ORANGE,
)

metric_aws_http_503_perc = metrics.Metric(
    name="aws_http_503_perc",
    title=Localizable("Percentage of HTTP 503 errors"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_ORANGE,
)

metric_aws_http_504_rate = metrics.Metric(
    name="aws_http_504_rate",
    title=Localizable("HTTP 504 errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_http_504_perc = metrics.Metric(
    name="aws_http_504_perc",
    title=Localizable("Percentage of HTTP 504 errors"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_users_errors_rate = metrics.Metric(
    name="aws_lambda_users_errors_rate",
    title=Localizable("Lambda user errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_users_errors_perc = metrics.Metric(
    name="aws_lambda_users_errors_perc",
    title=Localizable("Percentage of Lambda user errors"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_overall_hosts_health_perc = metrics.Metric(
    name="aws_overall_hosts_health_perc",
    title=Localizable("Proportion of healthy host"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_backend_connection_errors_rate = metrics.Metric(
    name="aws_backend_connection_errors_rate",
    title=Localizable("Backend connection errors"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_burst_balance = metrics.Metric(
    name="aws_burst_balance",
    title=Localizable("Burst Balance"),
    unit=Unit.PERCENTAGE,
    color=Color.PURPLE,
)

metric_aws_cpu_credit_balance = metrics.Metric(
    name="aws_cpu_credit_balance",
    title=Localizable("CPU Credit Balance"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_rds_bin_log_disk_usage = metrics.Metric(
    name="aws_rds_bin_log_disk_usage",
    title=Localizable("Bin Log Disk Usage"),
    unit=Unit.PERCENTAGE,
    color=Color.PURPLE,
)

metric_aws_rds_transaction_logs_disk_usage = metrics.Metric(
    name="aws_rds_transaction_logs_disk_usage",
    title=Localizable("Transaction Logs Disk Usage"),
    unit=Unit.PERCENTAGE,
    color=Color.PURPLE,
)

metric_aws_rds_replication_slot_disk_usage = metrics.Metric(
    name="aws_rds_replication_slot_disk_usage",
    title=Localizable("Replication Slot Disk Usage"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_PURPLE,
)

metric_aws_rds_replica_lag = metrics.Metric(
    name="aws_rds_replica_lag",
    title=Localizable("Replica Lag"),
    unit=Unit.SECOND,
    color=Color.ORANGE,
)

metric_aws_rds_oldest_replication_slot_lag = metrics.Metric(
    name="aws_rds_oldest_replication_slot_lag",
    title=Localizable("Oldest Replication Slot Lag Size"),
    unit=Unit.BYTES_IEC,
    color=Color.ORANGE,
)

metric_aws_rds_connections = metrics.Metric(
    name="aws_rds_connections",
    title=Localizable("Connections in use"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_request_latency = metrics.Metric(
    name="aws_request_latency",
    title=Localizable("Request latency"),
    unit=Unit.SECOND,
    color=Color.YELLOW,
)

metric_aws_ec2_vpc_elastic_ip_addresses = metrics.Metric(
    name="aws_ec2_vpc_elastic_ip_addresses",
    title=Localizable("VPC Elastic IP Addresses"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_elastic_ip_addresses = metrics.Metric(
    name="aws_ec2_elastic_ip_addresses",
    title=Localizable("Elastic IP Addresses"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_spot_inst_requests = metrics.Metric(
    name="aws_ec2_spot_inst_requests",
    title=Localizable("Spot Instance Requests"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_ec2_active_spot_fleet_requests = metrics.Metric(
    name="aws_ec2_active_spot_fleet_requests",
    title=Localizable("Active Spot Fleet Requests"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_spot_fleet_total_target_capacity = metrics.Metric(
    name="aws_ec2_spot_fleet_total_target_capacity",
    title=Localizable("Spot Fleet Requests Total Target Capacity"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_total = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_total",
    title=Localizable("Total running On-Demand Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_a1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.2xlarge",
    title=Localizable("Total running On-Demand a1.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.4xlarge",
    title=Localizable("Total running On-Demand a1.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_a1_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.large",
    title=Localizable("Total running On-Demand a1.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_a1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.medium",
    title=Localizable("Total running On-Demand a1.medium Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_a1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.metal",
    title=Localizable("Total running On-Demand a1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_a1.xlarge",
    title=Localizable("Total running On-Demand a1.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c1.medium",
    title=Localizable("Total running On-Demand c1.medium Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c1.xlarge",
    title=Localizable("Total running On-Demand c1.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.2xlarge",
    title=Localizable("Total running On-Demand c3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.4xlarge",
    title=Localizable("Total running On-Demand c3.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.8xlarge",
    title=Localizable("Total running On-Demand c3.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.large",
    title=Localizable("Total running On-Demand c3.large Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c3.xlarge",
    title=Localizable("Total running On-Demand c3.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.2xlarge",
    title=Localizable("Total running On-Demand c4.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.4xlarge",
    title=Localizable("Total running On-Demand c4.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c4_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.8xlarge",
    title=Localizable("Total running On-Demand c4.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.large",
    title=Localizable("Total running On-Demand c4.large Instances"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.xlarge",
    title=Localizable("Total running On-Demand c4.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.12xlarge",
    title=Localizable("Total running On-Demand c5.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.18xlarge",
    title=Localizable("Total running On-Demand c5.18xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.24xlarge",
    title=Localizable("Total running On-Demand c5.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.2xlarge",
    title=Localizable("Total running On-Demand c5.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.4xlarge",
    title=Localizable("Total running On-Demand c5.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.9xlarge",
    title=Localizable("Total running On-Demand c5.9xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.large",
    title=Localizable("Total running On-Demand c5.large Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.metal",
    title=Localizable("Total running On-Demand c5.metal Instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5.xlarge",
    title=Localizable("Total running On-Demand c5.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.12xlarge",
    title=Localizable("Total running On-Demand c5a.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.16xlarge",
    title=Localizable("Total running On-Demand c5a.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.24xlarge",
    title=Localizable("Total running On-Demand c5a.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.2xlarge",
    title=Localizable("Total running On-Demand c5a.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.4xlarge",
    title=Localizable("Total running On-Demand c5a.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.8xlarge",
    title=Localizable("Total running On-Demand c5a.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.large",
    title=Localizable("Total running On-Demand c5a.large Instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5a.xlarge",
    title=Localizable("Total running On-Demand c5a.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.12xlarge",
    title=Localizable("Total running On-Demand c5ad.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.16xlarge",
    title=Localizable("Total running On-Demand c5ad.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.24xlarge",
    title=Localizable("Total running On-Demand c5ad.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.2xlarge",
    title=Localizable("Total running On-Demand c5ad.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.4xlarge",
    title=Localizable("Total running On-Demand c5ad.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.8xlarge",
    title=Localizable("Total running On-Demand c5ad.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.large",
    title=Localizable("Total running On-Demand c5ad.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5ad.xlarge",
    title=Localizable("Total running On-Demand c5ad.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.12xlarge",
    title=Localizable("Total running On-Demand c5d.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.18xlarge",
    title=Localizable("Total running On-Demand c5d.18xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.24xlarge",
    title=Localizable("Total running On-Demand c5d.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.2xlarge",
    title=Localizable("Total running On-Demand c5d.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.4xlarge",
    title=Localizable("Total running On-Demand c5d.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.9xlarge",
    title=Localizable("Total running On-Demand c5d.9xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.large",
    title=Localizable("Total running On-Demand c5d.large Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.metal",
    title=Localizable("Total running On-Demand c5d.metal Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5d.xlarge",
    title=Localizable("Total running On-Demand c5d.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5n_18xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.18xlarge",
    title=Localizable("Total running On-Demand c5n.18xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.2xlarge",
    title=Localizable("Total running On-Demand c5n.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.4xlarge",
    title=Localizable("Total running On-Demand c5n.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c5n_9xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.9xlarge",
    title=Localizable("Total running On-Demand c5n.9xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.large",
    title=Localizable("Total running On-Demand c5n.large Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.metal",
    title=Localizable("Total running On-Demand c5n.metal Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c5n.xlarge",
    title=Localizable("Total running On-Demand c5n.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.12xlarge",
    title=Localizable("Total running On-Demand c6g.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.16xlarge",
    title=Localizable("Total running On-Demand c6g.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.2xlarge",
    title=Localizable("Total running On-Demand c6g.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.4xlarge",
    title=Localizable("Total running On-Demand c6g.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.8xlarge",
    title=Localizable("Total running On-Demand c6g.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.large",
    title=Localizable("Total running On-Demand c6g.large Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.medium",
    title=Localizable("Total running On-Demand c6g.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.metal",
    title=Localizable("Total running On-Demand c6g.metal Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6g.xlarge",
    title=Localizable("Total running On-Demand c6g.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.12xlarge",
    title=Localizable("Total running On-Demand c6gd.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.16xlarge",
    title=Localizable("Total running On-Demand c6gd.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.2xlarge",
    title=Localizable("Total running On-Demand c6gd.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.4xlarge",
    title=Localizable("Total running On-Demand c6gd.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.8xlarge",
    title=Localizable("Total running On-Demand c6gd.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.large",
    title=Localizable("Total running On-Demand c6gd.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.medium",
    title=Localizable("Total running On-Demand c6gd.medium Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.metal",
    title=Localizable("Total running On-Demand c6gd.metal Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gd.xlarge",
    title=Localizable("Total running On-Demand c6gd.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.12xlarge",
    title=Localizable("Total running On-Demand c6gn.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.16xlarge",
    title=Localizable("Total running On-Demand c6gn.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.2xlarge",
    title=Localizable("Total running On-Demand c6gn.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.4xlarge",
    title=Localizable("Total running On-Demand c6gn.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.8xlarge",
    title=Localizable("Total running On-Demand c6gn.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.large",
    title=Localizable("Total running On-Demand c6gn.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gn_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.medium",
    title=Localizable("Total running On-Demand c6gn.medium Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c6gn.xlarge",
    title=Localizable("Total running On-Demand c6gn.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_cc1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cc1.4xlarge",
    title=Localizable("Total running On-Demand cc1.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_cc2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cc2.8xlarge",
    title=Localizable("Total running On-Demand cc2.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_cg1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cg1.4xlarge",
    title=Localizable("Total running On-Demand cg1.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_cr1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_cr1.8xlarge",
    title=Localizable("Total running On-Demand cr1.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.2xlarge",
    title=Localizable("Total running On-Demand d2.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_d2_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.4xlarge",
    title=Localizable("Total running On-Demand d2.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.8xlarge",
    title=Localizable("Total running On-Demand d2.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d2.xlarge",
    title=Localizable("Total running On-Demand d2.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.2xlarge",
    title=Localizable("Total running On-Demand d3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.4xlarge",
    title=Localizable("Total running On-Demand d3.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.8xlarge",
    title=Localizable("Total running On-Demand d3.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3.xlarge",
    title=Localizable("Total running On-Demand d3.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_d3en_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.12xlarge",
    title=Localizable("Total running On-Demand d3en.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d3en_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.2xlarge",
    title=Localizable("Total running On-Demand d3en.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3en_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.4xlarge",
    title=Localizable("Total running On-Demand d3en.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3en_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.6xlarge",
    title=Localizable("Total running On-Demand d3en.6xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3en_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.8xlarge",
    title=Localizable("Total running On-Demand d3en.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3en_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_d3en.xlarge",
    title=Localizable("Total running On-Demand d3en.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_f1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f1.16xlarge",
    title=Localizable("Total running On-Demand f1.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_f1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f1.2xlarge",
    title=Localizable("Total running On-Demand f1.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_f1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f1.4xlarge",
    title=Localizable("Total running On-Demand f1.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g2.2xlarge",
    title=Localizable("Total running On-Demand g2.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g2.8xlarge",
    title=Localizable("Total running On-Demand g2.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.16xlarge",
    title=Localizable("Total running On-Demand g3.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.4xlarge",
    title=Localizable("Total running On-Demand g3.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3.8xlarge",
    title=Localizable("Total running On-Demand g3.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g3s_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g3s.xlarge",
    title=Localizable("Total running On-Demand g3s.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.16xlarge",
    title=Localizable("Total running On-Demand g4ad.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.2xlarge",
    title=Localizable("Total running On-Demand g4ad.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.4xlarge",
    title=Localizable("Total running On-Demand g4ad.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.8xlarge",
    title=Localizable("Total running On-Demand g4ad.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4ad.xlarge",
    title=Localizable("Total running On-Demand g4ad.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.12xlarge",
    title=Localizable("Total running On-Demand g4dn.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g4dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.16xlarge",
    title=Localizable("Total running On-Demand g4dn.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.2xlarge",
    title=Localizable("Total running On-Demand g4dn.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.4xlarge",
    title=Localizable("Total running On-Demand g4dn.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.8xlarge",
    title=Localizable("Total running On-Demand g4dn.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.metal",
    title=Localizable("Total running On-Demand g4dn.metal Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g4dn.xlarge",
    title=Localizable("Total running On-Demand g4dn.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.16xlarge",
    title=Localizable("Total running On-Demand h1.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_h1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.2xlarge",
    title=Localizable("Total running On-Demand h1.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_h1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.4xlarge",
    title=Localizable("Total running On-Demand h1.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_h1.8xlarge",
    title=Localizable("Total running On-Demand h1.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_hi1_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_hi1.4xlarge",
    title=Localizable("Total running On-Demand hi1.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_hs1_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_hs1.8xlarge",
    title=Localizable("Total running On-Demand hs1.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.2xlarge",
    title=Localizable("Total running On-Demand i2.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i2_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.4xlarge",
    title=Localizable("Total running On-Demand i2.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.8xlarge",
    title=Localizable("Total running On-Demand i2.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i2.xlarge",
    title=Localizable("Total running On-Demand i2.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.16xlarge",
    title=Localizable("Total running On-Demand i3.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.2xlarge",
    title=Localizable("Total running On-Demand i3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.4xlarge",
    title=Localizable("Total running On-Demand i3.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.8xlarge",
    title=Localizable("Total running On-Demand i3.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.large",
    title=Localizable("Total running On-Demand i3.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.metal",
    title=Localizable("Total running On-Demand i3.metal Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3.xlarge",
    title=Localizable("Total running On-Demand i3.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.12xlarge",
    title=Localizable("Total running On-Demand i3en.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3en_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.24xlarge",
    title=Localizable("Total running On-Demand i3en.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3en_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.2xlarge",
    title=Localizable("Total running On-Demand i3en.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3en_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.3xlarge",
    title=Localizable("Total running On-Demand i3en.3xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.6xlarge",
    title=Localizable("Total running On-Demand i3en.6xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3en_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.large",
    title=Localizable("Total running On-Demand i3en.large Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3en_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.metal",
    title=Localizable("Total running On-Demand i3en.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i3en.xlarge",
    title=Localizable("Total running On-Demand i3en.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_inf1_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.24xlarge",
    title=Localizable("Total running On-Demand inf1.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_inf1_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.2xlarge",
    title=Localizable("Total running On-Demand inf1.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_inf1_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.6xlarge",
    title=Localizable("Total running On-Demand inf1.6xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_inf1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_inf1.xlarge",
    title=Localizable("Total running On-Demand inf1.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m1_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.large",
    title=Localizable("Total running On-Demand m1.large Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m1_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.medium",
    title=Localizable("Total running On-Demand m1.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m1_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.small",
    title=Localizable("Total running On-Demand m1.small Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m1_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m1.xlarge",
    title=Localizable("Total running On-Demand m1.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m2.2xlarge",
    title=Localizable("Total running On-Demand m2.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m2_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m2.4xlarge",
    title=Localizable("Total running On-Demand m2.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m2.xlarge",
    title=Localizable("Total running On-Demand m2.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.2xlarge",
    title=Localizable("Total running On-Demand m3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.large",
    title=Localizable("Total running On-Demand m3.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m3_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.medium",
    title=Localizable("Total running On-Demand m3.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m3.xlarge",
    title=Localizable("Total running On-Demand m3.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m4_10xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.10xlarge",
    title=Localizable("Total running On-Demand m4.10xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m4_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.16xlarge",
    title=Localizable("Total running On-Demand m4.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.2xlarge",
    title=Localizable("Total running On-Demand m4.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.4xlarge",
    title=Localizable("Total running On-Demand m4.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.large",
    title=Localizable("Total running On-Demand m4.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m4.xlarge",
    title=Localizable("Total running On-Demand m4.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.12xlarge",
    title=Localizable("Total running On-Demand m5.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.16xlarge",
    title=Localizable("Total running On-Demand m5.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.24xlarge",
    title=Localizable("Total running On-Demand m5.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.2xlarge",
    title=Localizable("Total running On-Demand m5.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.4xlarge",
    title=Localizable("Total running On-Demand m5.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.8xlarge",
    title=Localizable("Total running On-Demand m5.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.large",
    title=Localizable("Total running On-Demand m5.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.metal",
    title=Localizable("Total running On-Demand m5.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5.xlarge",
    title=Localizable("Total running On-Demand m5.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.12xlarge",
    title=Localizable("Total running On-Demand m5a.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.16xlarge",
    title=Localizable("Total running On-Demand m5a.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.24xlarge",
    title=Localizable("Total running On-Demand m5a.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.2xlarge",
    title=Localizable("Total running On-Demand m5a.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.4xlarge",
    title=Localizable("Total running On-Demand m5a.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.8xlarge",
    title=Localizable("Total running On-Demand m5a.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.large",
    title=Localizable("Total running On-Demand m5a.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5a.xlarge",
    title=Localizable("Total running On-Demand m5a.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.12xlarge",
    title=Localizable("Total running On-Demand m5ad.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.16xlarge",
    title=Localizable("Total running On-Demand m5ad.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5ad_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.24xlarge",
    title=Localizable("Total running On-Demand m5ad.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.2xlarge",
    title=Localizable("Total running On-Demand m5ad.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.4xlarge",
    title=Localizable("Total running On-Demand m5ad.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.8xlarge",
    title=Localizable("Total running On-Demand m5ad.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5ad_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.large",
    title=Localizable("Total running On-Demand m5ad.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5ad.xlarge",
    title=Localizable("Total running On-Demand m5ad.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.12xlarge",
    title=Localizable("Total running On-Demand m5d.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5d_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.16xlarge",
    title=Localizable("Total running On-Demand m5d.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.24xlarge",
    title=Localizable("Total running On-Demand m5d.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.2xlarge",
    title=Localizable("Total running On-Demand m5d.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.4xlarge",
    title=Localizable("Total running On-Demand m5d.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5d_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.8xlarge",
    title=Localizable("Total running On-Demand m5d.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.large",
    title=Localizable("Total running On-Demand m5d.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.metal",
    title=Localizable("Total running On-Demand m5d.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5d.xlarge",
    title=Localizable("Total running On-Demand m5d.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.12xlarge",
    title=Localizable("Total running On-Demand m5dn.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.16xlarge",
    title=Localizable("Total running On-Demand m5dn.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.24xlarge",
    title=Localizable("Total running On-Demand m5dn.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.2xlarge",
    title=Localizable("Total running On-Demand m5dn.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.4xlarge",
    title=Localizable("Total running On-Demand m5dn.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.8xlarge",
    title=Localizable("Total running On-Demand m5dn.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5dn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.large",
    title=Localizable("Total running On-Demand m5dn.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.metal",
    title=Localizable("Total running On-Demand m5dn.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5dn.xlarge",
    title=Localizable("Total running On-Demand m5dn.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5n_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.12xlarge",
    title=Localizable("Total running On-Demand m5n.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.16xlarge",
    title=Localizable("Total running On-Demand m5n.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.24xlarge",
    title=Localizable("Total running On-Demand m5n.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.2xlarge",
    title=Localizable("Total running On-Demand m5n.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.4xlarge",
    title=Localizable("Total running On-Demand m5n.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5n_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.8xlarge",
    title=Localizable("Total running On-Demand m5n.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.large",
    title=Localizable("Total running On-Demand m5n.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.metal",
    title=Localizable("Total running On-Demand m5n.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5n.xlarge",
    title=Localizable("Total running On-Demand m5n.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.12xlarge",
    title=Localizable("Total running On-Demand m5zn.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.2xlarge",
    title=Localizable("Total running On-Demand m5zn.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5zn_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.3xlarge",
    title=Localizable("Total running On-Demand m5zn.3xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.6xlarge",
    title=Localizable("Total running On-Demand m5zn.6xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.large",
    title=Localizable("Total running On-Demand m5zn.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.metal",
    title=Localizable("Total running On-Demand m5zn.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m5zn.xlarge",
    title=Localizable("Total running On-Demand m5zn.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.12xlarge",
    title=Localizable("Total running On-Demand m6g.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.16xlarge",
    title=Localizable("Total running On-Demand m6g.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.2xlarge",
    title=Localizable("Total running On-Demand m6g.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.4xlarge",
    title=Localizable("Total running On-Demand m6g.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.8xlarge",
    title=Localizable("Total running On-Demand m6g.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.large",
    title=Localizable("Total running On-Demand m6g.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.medium",
    title=Localizable("Total running On-Demand m6g.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.metal",
    title=Localizable("Total running On-Demand m6g.metal Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6g.xlarge",
    title=Localizable("Total running On-Demand m6g.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.12xlarge",
    title=Localizable("Total running On-Demand m6gd.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.16xlarge",
    title=Localizable("Total running On-Demand m6gd.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.2xlarge",
    title=Localizable("Total running On-Demand m6gd.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.4xlarge",
    title=Localizable("Total running On-Demand m6gd.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.8xlarge",
    title=Localizable("Total running On-Demand m6gd.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.large",
    title=Localizable("Total running On-Demand m6gd.large Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.medium",
    title=Localizable("Total running On-Demand m6gd.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.metal",
    title=Localizable("Total running On-Demand m6gd.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6gd.xlarge",
    title=Localizable("Total running On-Demand m6gd.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6i_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.12xlarge",
    title=Localizable("Total running On-Demand m6i.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6i_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.16xlarge",
    title=Localizable("Total running On-Demand m6i.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6i_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.24xlarge",
    title=Localizable("Total running On-Demand m6i.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6i_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.2xlarge",
    title=Localizable("Total running On-Demand m6i.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6i_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.32xlarge",
    title=Localizable("Total running On-Demand m6i.32xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6i_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.4xlarge",
    title=Localizable("Total running On-Demand m6i.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6i_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.8xlarge",
    title=Localizable("Total running On-Demand m6i.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6i_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.large",
    title=Localizable("Total running On-Demand m6i.large Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6i_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_m6i.xlarge",
    title=Localizable("Total running On-Demand m6i.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_mac1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_mac1.metal",
    title=Localizable("Total running On-Demand mac1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p2_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p2.16xlarge",
    title=Localizable("Total running On-Demand p2.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p2_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p2.8xlarge",
    title=Localizable("Total running On-Demand p2.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_p2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p2.xlarge",
    title=Localizable("Total running On-Demand p2.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_p3_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3.16xlarge",
    title=Localizable("Total running On-Demand p3.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_p3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3.2xlarge",
    title=Localizable("Total running On-Demand p3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_p3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3.8xlarge",
    title=Localizable("Total running On-Demand p3.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_p3dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p3dn.24xlarge",
    title=Localizable("Total running On-Demand p3dn.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p4d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p4d.24xlarge",
    title=Localizable("Total running On-Demand p4d.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.2xlarge",
    title=Localizable("Total running On-Demand r3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r3_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.4xlarge",
    title=Localizable("Total running On-Demand r3.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r3_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.8xlarge",
    title=Localizable("Total running On-Demand r3.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.large",
    title=Localizable("Total running On-Demand r3.large Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r3.xlarge",
    title=Localizable("Total running On-Demand r3.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r4_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.16xlarge",
    title=Localizable("Total running On-Demand r4.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.2xlarge",
    title=Localizable("Total running On-Demand r4.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.4xlarge",
    title=Localizable("Total running On-Demand r4.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r4_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.8xlarge",
    title=Localizable("Total running On-Demand r4.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.large",
    title=Localizable("Total running On-Demand r4.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r4.xlarge",
    title=Localizable("Total running On-Demand r4.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.12xlarge",
    title=Localizable("Total running On-Demand r5.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.16xlarge",
    title=Localizable("Total running On-Demand r5.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.24xlarge",
    title=Localizable("Total running On-Demand r5.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.2xlarge",
    title=Localizable("Total running On-Demand r5.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.4xlarge",
    title=Localizable("Total running On-Demand r5.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.8xlarge",
    title=Localizable("Total running On-Demand r5.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.large",
    title=Localizable("Total running On-Demand r5.large Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.metal",
    title=Localizable("Total running On-Demand r5.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5.xlarge",
    title=Localizable("Total running On-Demand r5.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.12xlarge",
    title=Localizable("Total running On-Demand r5a.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.16xlarge",
    title=Localizable("Total running On-Demand r5a.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5a_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.24xlarge",
    title=Localizable("Total running On-Demand r5a.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.2xlarge",
    title=Localizable("Total running On-Demand r5a.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5a_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.4xlarge",
    title=Localizable("Total running On-Demand r5a.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5a_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.8xlarge",
    title=Localizable("Total running On-Demand r5a.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.large",
    title=Localizable("Total running On-Demand r5a.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5a.xlarge",
    title=Localizable("Total running On-Demand r5a.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.12xlarge",
    title=Localizable("Total running On-Demand r5ad.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5ad_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.16xlarge",
    title=Localizable("Total running On-Demand r5ad.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5ad_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.24xlarge",
    title=Localizable("Total running On-Demand r5ad.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5ad_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.2xlarge",
    title=Localizable("Total running On-Demand r5ad.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5ad_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.4xlarge",
    title=Localizable("Total running On-Demand r5ad.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5ad_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.8xlarge",
    title=Localizable("Total running On-Demand r5ad.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.large",
    title=Localizable("Total running On-Demand r5ad.large Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5ad.xlarge",
    title=Localizable("Total running On-Demand r5ad.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.12xlarge",
    title=Localizable("Total running On-Demand r5b.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.16xlarge",
    title=Localizable("Total running On-Demand r5b.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5b_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.24xlarge",
    title=Localizable("Total running On-Demand r5b.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5b_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.2xlarge",
    title=Localizable("Total running On-Demand r5b.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5b_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.4xlarge",
    title=Localizable("Total running On-Demand r5b.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.8xlarge",
    title=Localizable("Total running On-Demand r5b.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.large",
    title=Localizable("Total running On-Demand r5b.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.metal",
    title=Localizable("Total running On-Demand r5b.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5b.xlarge",
    title=Localizable("Total running On-Demand r5b.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.12xlarge",
    title=Localizable("Total running On-Demand r5d.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.16xlarge",
    title=Localizable("Total running On-Demand r5d.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5d_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.24xlarge",
    title=Localizable("Total running On-Demand r5d.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.2xlarge",
    title=Localizable("Total running On-Demand r5d.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.4xlarge",
    title=Localizable("Total running On-Demand r5d.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5d_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.8xlarge",
    title=Localizable("Total running On-Demand r5d.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.large",
    title=Localizable("Total running On-Demand r5d.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.metal",
    title=Localizable("Total running On-Demand r5d.metal Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5d.xlarge",
    title=Localizable("Total running On-Demand r5d.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.12xlarge",
    title=Localizable("Total running On-Demand r5dn.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.16xlarge",
    title=Localizable("Total running On-Demand r5dn.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.24xlarge",
    title=Localizable("Total running On-Demand r5dn.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5dn_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.2xlarge",
    title=Localizable("Total running On-Demand r5dn.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5dn_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.4xlarge",
    title=Localizable("Total running On-Demand r5dn.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.8xlarge",
    title=Localizable("Total running On-Demand r5dn.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5dn_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.large",
    title=Localizable("Total running On-Demand r5dn.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.metal",
    title=Localizable("Total running On-Demand r5dn.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5dn.xlarge",
    title=Localizable("Total running On-Demand r5dn.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.12xlarge",
    title=Localizable("Total running On-Demand r5n.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5n_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.16xlarge",
    title=Localizable("Total running On-Demand r5n.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5n_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.24xlarge",
    title=Localizable("Total running On-Demand r5n.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5n_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.2xlarge",
    title=Localizable("Total running On-Demand r5n.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5n_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.4xlarge",
    title=Localizable("Total running On-Demand r5n.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5n_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.8xlarge",
    title=Localizable("Total running On-Demand r5n.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.large",
    title=Localizable("Total running On-Demand r5n.large Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.metal",
    title=Localizable("Total running On-Demand r5n.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5n_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r5n.xlarge",
    title=Localizable("Total running On-Demand r5n.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.12xlarge",
    title=Localizable("Total running On-Demand r6g.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.16xlarge",
    title=Localizable("Total running On-Demand r6g.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.2xlarge",
    title=Localizable("Total running On-Demand r6g.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6g_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.4xlarge",
    title=Localizable("Total running On-Demand r6g.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.8xlarge",
    title=Localizable("Total running On-Demand r6g.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.large",
    title=Localizable("Total running On-Demand r6g.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.medium",
    title=Localizable("Total running On-Demand r6g.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.metal",
    title=Localizable("Total running On-Demand r6g.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6g.xlarge",
    title=Localizable("Total running On-Demand r6g.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.12xlarge",
    title=Localizable("Total running On-Demand r6gd.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.16xlarge",
    title=Localizable("Total running On-Demand r6gd.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.2xlarge",
    title=Localizable("Total running On-Demand r6gd.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.4xlarge",
    title=Localizable("Total running On-Demand r6gd.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.8xlarge",
    title=Localizable("Total running On-Demand r6gd.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.large",
    title=Localizable("Total running On-Demand r6gd.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.medium",
    title=Localizable("Total running On-Demand r6gd.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.metal",
    title=Localizable("Total running On-Demand r6gd.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_r6gd.xlarge",
    title=Localizable("Total running On-Demand r6gd.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t1_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t1.micro",
    title=Localizable("Total running On-Demand t1.micro Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.2xlarge",
    title=Localizable("Total running On-Demand t2.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t2_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.large",
    title=Localizable("Total running On-Demand t2.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t2_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.medium",
    title=Localizable("Total running On-Demand t2.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t2_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.micro",
    title=Localizable("Total running On-Demand t2.micro Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t2_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.nano",
    title=Localizable("Total running On-Demand t2.nano Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t2_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.small",
    title=Localizable("Total running On-Demand t2.small Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t2.xlarge",
    title=Localizable("Total running On-Demand t2.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.2xlarge",
    title=Localizable("Total running On-Demand t3.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.large",
    title=Localizable("Total running On-Demand t3.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.medium",
    title=Localizable("Total running On-Demand t3.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.micro",
    title=Localizable("Total running On-Demand t3.micro Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.nano",
    title=Localizable("Total running On-Demand t3.nano Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.small",
    title=Localizable("Total running On-Demand t3.small Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3.xlarge",
    title=Localizable("Total running On-Demand t3.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.2xlarge",
    title=Localizable("Total running On-Demand t3a.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3a_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.large",
    title=Localizable("Total running On-Demand t3a.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3a_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.medium",
    title=Localizable("Total running On-Demand t3a.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3a_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.micro",
    title=Localizable("Total running On-Demand t3a.micro Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3a_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.nano",
    title=Localizable("Total running On-Demand t3a.nano Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3a_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.small",
    title=Localizable("Total running On-Demand t3a.small Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t3a.xlarge",
    title=Localizable("Total running On-Demand t3a.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.2xlarge",
    title=Localizable("Total running On-Demand t4g.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t4g_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.large",
    title=Localizable("Total running On-Demand t4g.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t4g_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.medium",
    title=Localizable("Total running On-Demand t4g.medium Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t4g_micro = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.micro",
    title=Localizable("Total running On-Demand t4g.micro Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t4g_nano = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.nano",
    title=Localizable("Total running On-Demand t4g.nano Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t4g_small = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.small",
    title=Localizable("Total running On-Demand t4g.small Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_t4g.xlarge",
    title=Localizable("Total running On-Demand t4g.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_12tb1_112xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-12tb1.112xlarge",
    title=Localizable("Total running On-Demand u-12tb1.112xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_12tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-12tb1.metal",
    title=Localizable("Total running On-Demand u-12tb1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_u_18tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-18tb1.metal",
    title=Localizable("Total running On-Demand u-18tb1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_u_24tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-24tb1.metal",
    title=Localizable("Total running On-Demand u-24tb1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_112xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-6tb1.112xlarge",
    title=Localizable("Total running On-Demand u-6tb1.112xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_56xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-6tb1.56xlarge",
    title=Localizable("Total running On-Demand u-6tb1.56xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-6tb1.metal",
    title=Localizable("Total running On-Demand u-6tb1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_9tb1_112xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-9tb1.112xlarge",
    title=Localizable("Total running On-Demand u-9tb1.112xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_9tb1_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_u-9tb1.metal",
    title=Localizable("Total running On-Demand u-9tb1.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_vt1_24xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.24xlarge",
    title=Localizable("Total running On-Demand vt1.24xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_vt1_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.3xlarge",
    title=Localizable("Total running On-Demand vt1.3xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_vt1_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_vt1.6xlarge",
    title=Localizable("Total running On-Demand vt1.6xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1.16xlarge",
    title=Localizable("Total running On-Demand x1.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1.32xlarge",
    title=Localizable("Total running On-Demand x1.32xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1e_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.16xlarge",
    title=Localizable("Total running On-Demand x1e.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.2xlarge",
    title=Localizable("Total running On-Demand x1e.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x1e_32xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.32xlarge",
    title=Localizable("Total running On-Demand x1e.32xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x1e_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.4xlarge",
    title=Localizable("Total running On-Demand x1e.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x1e_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.8xlarge",
    title=Localizable("Total running On-Demand x1e.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x1e.xlarge",
    title=Localizable("Total running On-Demand x1e.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.12xlarge",
    title=Localizable("Total running On-Demand x2gd.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_16xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.16xlarge",
    title=Localizable("Total running On-Demand x2gd.16xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.2xlarge",
    title=Localizable("Total running On-Demand x2gd.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.4xlarge",
    title=Localizable("Total running On-Demand x2gd.4xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x2gd_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.8xlarge",
    title=Localizable("Total running On-Demand x2gd.8xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.large",
    title=Localizable("Total running On-Demand x2gd.large Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_medium = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.medium",
    title=Localizable("Total running On-Demand x2gd.medium Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.metal",
    title=Localizable("Total running On-Demand x2gd.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x2gd.xlarge",
    title=Localizable("Total running On-Demand x2gd.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_12xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.12xlarge",
    title=Localizable("Total running On-Demand z1d.12xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_z1d_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.2xlarge",
    title=Localizable("Total running On-Demand z1d.2xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_z1d_3xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.3xlarge",
    title=Localizable("Total running On-Demand z1d.3xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_z1d_6xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.6xlarge",
    title=Localizable("Total running On-Demand z1d.6xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.large",
    title=Localizable("Total running On-Demand z1d.large Instances"),
    unit=Unit.COUNT,
    color=Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_metal = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.metal",
    title=Localizable("Total running On-Demand z1d.metal Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_z1d.xlarge",
    title=Localizable("Total running On-Demand z1d.xlarge Instances"),
    unit=Unit.COUNT,
    color=Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_f_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_f_vcpu",
    title=Localizable("Total title=Localizable('Running On-Demand F instances') vCPUs"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_g_vcpu",
    title=Localizable("Total title=Localizable('Running On-Demand G instances') vCPUs"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_i_vcpu",
    title=Localizable("Total title=Localizable('Running On-Demand Inf instances') vCPUs"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_p_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_p_vcpu",
    title=Localizable("Total title=Localizable('Running On-Demand P instances') vCPUs"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_x_vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_x_vcpu",
    title=Localizable("Total title=Localizable('Running On-Demand X instances') vCPUs"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances___vcpu = metrics.Metric(
    name="aws_ec2_running_ondemand_instances___vcpu",
    title=Localizable(
        "Total title=Localizable('Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances') vCPUs"
    ),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_consumed_lcus = metrics.Metric(
    name="aws_consumed_lcus",
    title=Localizable("Consumed Load Balancer Capacity unit=Units"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_active_connections = metrics.Metric(
    name="aws_active_connections",
    title=Localizable("Active Connections"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_active_tls_connections = metrics.Metric(
    name="aws_active_tls_connections",
    title=Localizable("Active TLS Connections"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_new_connections = metrics.Metric(
    name="aws_new_connections",
    title=Localizable("New Connections"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_PURPLE,
)

metric_aws_new_tls_connections = metrics.Metric(
    name="aws_new_tls_connections",
    title=Localizable("New TLS Connections"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_rejected_connections = metrics.Metric(
    name="aws_rejected_connections",
    title=Localizable("Rejected Connections"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_client_tls_errors = metrics.Metric(
    name="aws_client_tls_errors",
    title=Localizable("Client TLS errors"),
    unit=Unit.PER_SECOND,
    color=Color.YELLOW,
)

metric_aws_http_redirects = metrics.Metric(
    name="aws_http_redirects",
    title=Localizable("HTTP Redirects"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_http_redirect_url_limit = metrics.Metric(
    name="aws_http_redirect_url_limit",
    title=Localizable("HTTP Redirects URL Limit Exceeded"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_http_fixed_response = metrics.Metric(
    name="aws_http_fixed_response",
    title=Localizable("HTTP Fixed Responses"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_proc_bytes = metrics.Metric(
    name="aws_proc_bytes",
    title=Localizable("Processed Bytes"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_proc_bytes_tls = metrics.Metric(
    name="aws_proc_bytes_tls",
    title=Localizable("TLS Processed Bytes"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_ipv6_proc_bytes = metrics.Metric(
    name="aws_ipv6_proc_bytes",
    title=Localizable("IPv6 Processed Bytes"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ipv6_requests = metrics.Metric(
    name="aws_ipv6_requests",
    title=Localizable("IPv6 Requests"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_rule_evaluations = metrics.Metric(
    name="aws_rule_evaluations",
    title=Localizable("Rule Evaluations"),
    unit=Unit.PER_SECOND,
    color=Color.YELLOW,
)

metric_aws_failed_tls_client_handshake = metrics.Metric(
    name="aws_failed_tls_client_handshake",
    title=Localizable("Failed TLS Client Handshake"),
    unit=Unit.PER_SECOND,
    color=Color.YELLOW,
)

metric_aws_failed_tls_target_handshake = metrics.Metric(
    name="aws_failed_tls_target_handshake",
    title=Localizable("Failed TLS Target Handshake"),
    unit=Unit.PER_SECOND,
    color=Color.YELLOW,
)

metric_aws_tcp_client_rst = metrics.Metric(
    name="aws_tcp_client_rst",
    title=Localizable("TCP Client Resets"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_GREEN,
)

metric_aws_tcp_elb_rst = metrics.Metric(
    name="aws_tcp_elb_rst",
    title=Localizable("TCP ELB Resets"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_tcp_target_rst = metrics.Metric(
    name="aws_tcp_target_rst",
    title=Localizable("TCP Target Resets"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_s3_downloads = metrics.Metric(
    name="aws_s3_downloads",
    title=Localizable("Download"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.YELLOW,
)

metric_aws_s3_uploads = metrics.Metric(
    name="aws_s3_uploads",
    title=Localizable("Upload"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.LIGHT_GREEN,
)

metric_aws_s3_select_object_scanned = metrics.Metric(
    name="aws_s3_select_object_scanned",
    title=Localizable("SELECT Object Scanned"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.LIGHT_GREEN,
)

metric_aws_s3_select_object_returned = metrics.Metric(
    name="aws_s3_select_object_returned",
    title=Localizable("SELECT Object Returned"),
    unit=Unit.BYTES_IEC_PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_s3_buckets = metrics.Metric(
    name="aws_s3_buckets",
    title=Localizable("Buckets"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_elb_load_balancers = metrics.Metric(
    name="aws_elb_load_balancers",
    title=Localizable("Load balancers"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_elb_load_balancer_listeners = metrics.Metric(
    name="aws_elb_load_balancer_listeners",
    title=Localizable("Load balancer listeners"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_elb_load_balancer_registered_instances = metrics.Metric(
    name="aws_elb_load_balancer_registered_instances",
    title=Localizable("Load balancer registered instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_rds_db_clusters = metrics.Metric(
    name="aws_rds_db_clusters",
    title=Localizable("DB clusters"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_rds_db_cluster_parameter_groups = metrics.Metric(
    name="aws_rds_db_cluster_parameter_groups",
    title=Localizable("DB cluster parameter groups"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_rds_db_instances = metrics.Metric(
    name="aws_rds_db_instances",
    title=Localizable("DB instances"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_rds_event_subscriptions = metrics.Metric(
    name="aws_rds_event_subscriptions",
    title=Localizable("Event subscriptions"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_rds_manual_snapshots = metrics.Metric(
    name="aws_rds_manual_snapshots",
    title=Localizable("Manual snapshots"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_rds_option_groups = metrics.Metric(
    name="aws_rds_option_groups",
    title=Localizable("Option groups"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_rds_db_parameter_groups = metrics.Metric(
    name="aws_rds_db_parameter_groups",
    title=Localizable("DB parameter groups"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_rds_read_replica_per_master = metrics.Metric(
    name="aws_rds_read_replica_per_master",
    title=Localizable("Read replica per master"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_rds_reserved_db_instances = metrics.Metric(
    name="aws_rds_reserved_db_instances",
    title=Localizable("Reserved DB instances"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_rds_db_security_groups = metrics.Metric(
    name="aws_rds_db_security_groups",
    title=Localizable("DB security groups"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_rds_db_subnet_groups = metrics.Metric(
    name="aws_rds_db_subnet_groups",
    title=Localizable("DB subnet groups"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_rds_subnet_per_db_subnet_groups = metrics.Metric(
    name="aws_rds_subnet_per_db_subnet_groups",
    title=Localizable("Subnet per DB subnet groups"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_rds_allocated_storage = metrics.Metric(
    name="aws_rds_allocated_storage",
    title=Localizable("Allocated storage"),
    unit=Unit.BYTES_IEC,
    color=Color.LIGHT_GREEN,
)

metric_aws_rds_auths_per_db_security_groups = metrics.Metric(
    name="aws_rds_auths_per_db_security_groups",
    title=Localizable("Authorizations per DB security group"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_rds_db_cluster_roles = metrics.Metric(
    name="aws_rds_db_cluster_roles",
    title=Localizable("DB cluster roles"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_ebs_block_store_snapshots = metrics.Metric(
    name="aws_ebs_block_store_snapshots",
    title=Localizable("Block store snapshots"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_ebs_block_store_space_standard = metrics.Metric(
    name="aws_ebs_block_store_space_standard",
    title=Localizable("Magnetic volumes space"),
    unit=Unit.BYTES_IEC,
    color=Color.PURPLE,
)

metric_aws_ebs_block_store_space_io1 = metrics.Metric(
    name="aws_ebs_block_store_space_io1",
    title=Localizable("Provisioned IOPS SSD (io1) space"),
    unit=Unit.BYTES_IEC,
    color=Color.LIGHT_PURPLE,
)

metric_aws_ebs_block_store_iops_io1 = metrics.Metric(
    name="aws_ebs_block_store_iops_io1",
    title=Localizable("Provisioned IOPS SSD (io1) IO operations per second"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_ebs_block_store_space_io2 = metrics.Metric(
    name="aws_ebs_block_store_space_io2",
    title=Localizable("Provisioned IOPS SSD (io2) space"),
    unit=Unit.BYTES_IEC,
    color=Color.YELLOW,
)

metric_aws_ebs_block_store_iops_io2 = metrics.Metric(
    name="aws_ebs_block_store_iops_io2",
    title=Localizable("Provisioned IOPS SSD (io2) IO operations per second"),
    unit=Unit.PER_SECOND,
    color=Color.YELLOW,
)

metric_aws_ebs_block_store_space_gp2 = metrics.Metric(
    name="aws_ebs_block_store_space_gp2",
    title=Localizable("General Purpose SSD (gp2) space"),
    unit=Unit.BYTES_IEC,
    color=Color.ORANGE,
)

metric_aws_ebs_block_store_space_gp3 = metrics.Metric(
    name="aws_ebs_block_store_space_gp3",
    title=Localizable("General Purpose SSD (gp3) space"),
    unit=Unit.BYTES_IEC,
    color=Color.YELLOW,
)

metric_aws_ebs_block_store_space_sc1 = metrics.Metric(
    name="aws_ebs_block_store_space_sc1",
    title=Localizable("Cold HDD space"),
    unit=Unit.BYTES_IEC,
    color=Color.ORANGE,
)

metric_aws_ebs_block_store_space_st1 = metrics.Metric(
    name="aws_ebs_block_store_space_st1",
    title=Localizable("Throughput Optimized HDD space"),
    unit=Unit.BYTES_IEC,
    color=Color.YELLOW,
)

metric_aws_elbv2_application_load_balancers = metrics.Metric(
    name="aws_elbv2_application_load_balancers",
    title=Localizable("Application Load balancers"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_elbv2_application_load_balancer_rules = metrics.Metric(
    name="aws_elbv2_application_load_balancer_rules",
    title=Localizable("Application Load Balancer Rules"),
    unit=Unit.COUNT,
    color=Color.LIGHT_PURPLE,
)

metric_aws_elbv2_application_load_balancer_listeners = metrics.Metric(
    name="aws_elbv2_application_load_balancer_listeners",
    title=Localizable("Application Load Balancer Listeners"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_elbv2_application_load_balancer_target_groups = metrics.Metric(
    name="aws_elbv2_application_load_balancer_target_groups",
    title=Localizable("Application Load Balancer Target Groups"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_elbv2_application_load_balancer_certificates = metrics.Metric(
    name="aws_elbv2_application_load_balancer_certificates",
    title=Localizable("Application Load balancer Certificates"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_elbv2_network_load_balancers = metrics.Metric(
    name="aws_elbv2_network_load_balancers",
    title=Localizable("Network Load balancers"),
    unit=Unit.COUNT,
    color=Color.DARK_YELLOW,
)

metric_aws_elbv2_network_load_balancer_listeners = metrics.Metric(
    name="aws_elbv2_network_load_balancer_listeners",
    title=Localizable("Network Load Balancer Listeners"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_elbv2_network_load_balancer_target_groups = metrics.Metric(
    name="aws_elbv2_network_load_balancer_target_groups",
    title=Localizable("Network Load Balancer Target Groups"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_elbv2_load_balancer_target_groups = metrics.Metric(
    name="aws_elbv2_load_balancer_target_groups",
    title=Localizable("Load balancers Target Groups"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_number_of_tables = metrics.Metric(
    name="aws_dynamodb_number_of_tables",
    title=Localizable("Number of tables"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_dynamodb_read_capacity = metrics.Metric(
    name="aws_dynamodb_read_capacity",
    title=Localizable("Read Capacity"),
    unit=Unit.READ_CAPACITY_UNIT,
    color=Color.ORANGE,
)

metric_aws_dynamodb_write_capacity = metrics.Metric(
    name="aws_dynamodb_write_capacity",
    title=Localizable("Write Capacity"),
    unit=Unit.WRITE_CAPACITY_UNIT,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_consumed_rcu",
    title=Localizable("Average consumption"),
    unit=Unit.READ_CAPACITY_UNIT,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_rcu_perc = metrics.Metric(
    name="aws_dynamodb_consumed_rcu_perc",
    title=Localizable("Average usage"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_wcu = metrics.Metric(
    name="aws_dynamodb_consumed_wcu",
    title=Localizable("Average consumption"),
    unit=Unit.WRITE_CAPACITY_UNIT,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_wcu_perc = metrics.Metric(
    name="aws_dynamodb_consumed_wcu_perc",
    title=Localizable("Average usage"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_minimum_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_minimum_consumed_rcu",
    title=Localizable("Minimum single-request consumption"),
    unit=Unit.READ_CAPACITY_UNIT,
    color=Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_maximum_consumed_rcu",
    title=Localizable("Maximum single-request consumption"),
    unit=Unit.READ_CAPACITY_UNIT,
    color=Color.ORANGE,
)

metric_aws_dynamodb_minimum_consumed_wcu = metrics.Metric(
    name="aws_dynamodb_minimum_consumed_wcu",
    title=Localizable("Minimum single-request consumption"),
    unit=Unit.WRITE_CAPACITY_UNIT,
    color=Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_wcu = metrics.Metric(
    name="aws_dynamodb_maximum_consumed_wcu",
    title=Localizable("Maximum single-request consumption"),
    unit=Unit.WRITE_CAPACITY_UNIT,
    color=Color.ORANGE,
)

metric_aws_dynamodb_query_average_latency = metrics.Metric(
    name="aws_dynamodb_query_average_latency",
    title=Localizable("Average latency of successful Query requests"),
    unit=Unit.SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_query_maximum_latency = metrics.Metric(
    name="aws_dynamodb_query_maximum_latency",
    title=Localizable("Maximum latency of successful Query requests"),
    unit=Unit.SECOND,
    color=Color.ORANGE,
)

metric_aws_dynamodb_getitem_average_latency = metrics.Metric(
    name="aws_dynamodb_getitem_average_latency",
    title=Localizable("Average latency of successful GetItem requests"),
    unit=Unit.SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_getitem_maximum_latency = metrics.Metric(
    name="aws_dynamodb_getitem_maximum_latency",
    title=Localizable("Maximum latency of successful GetItem requests"),
    unit=Unit.SECOND,
    color=Color.ORANGE,
)

metric_aws_dynamodb_putitem_average_latency = metrics.Metric(
    name="aws_dynamodb_putitem_average_latency",
    title=Localizable("Average latency of successful PutItem requests"),
    unit=Unit.SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_dynamodb_putitem_maximum_latency = metrics.Metric(
    name="aws_dynamodb_putitem_maximum_latency",
    title=Localizable("Maximum latency of successful PutItem requests"),
    unit=Unit.SECOND,
    color=Color.ORANGE,
)

metric_aws_wafv2_web_acls = metrics.Metric(
    name="aws_wafv2_web_acls",
    title=Localizable("Number of Web ACLs"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_wafv2_rule_groups = metrics.Metric(
    name="aws_wafv2_rule_groups",
    title=Localizable("Number of rule groups"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_aws_wafv2_ip_sets = metrics.Metric(
    name="aws_wafv2_ip_sets",
    title=Localizable("Number of IP sets"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_wafv2_regex_pattern_sets = metrics.Metric(
    name="aws_wafv2_regex_pattern_sets",
    title=Localizable("Number of regex sets"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_wafv2_web_acl_capacity_units = metrics.Metric(
    name="aws_wafv2_web_acl_capacity_units",
    title=Localizable("Web ACL capacity units (WCUs)"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_wafv2_requests_rate = metrics.Metric(
    name="aws_wafv2_requests_rate",
    title=Localizable("Avg. request rate"),
    unit=Unit.PER_SECOND,
    color=Color.DARK_BROWN,
)

metric_aws_wafv2_allowed_requests_rate = metrics.Metric(
    name="aws_wafv2_allowed_requests_rate",
    title=Localizable("Avg. rate of allowed requests"),
    unit=Unit.PER_SECOND,
    color=Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_rate = metrics.Metric(
    name="aws_wafv2_blocked_requests_rate",
    title=Localizable("Avg. rate of blocked requests"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_wafv2_allowed_requests_perc = metrics.Metric(
    name="aws_wafv2_allowed_requests_perc",
    title=Localizable("Percentage of allowed requests"),
    unit=Unit.PERCENTAGE,
    color=Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_perc = metrics.Metric(
    name="aws_wafv2_blocked_requests_perc",
    title=Localizable("Percentage of blocked requests"),
    unit=Unit.PERCENTAGE,
    color=Color.ORANGE,
)

metric_aws_cloudwatch_alarms_cloudwatch_alarms = metrics.Metric(
    name="aws_cloudwatch_alarms_cloudwatch_alarms",
    title=Localizable("CloudWatch alarms"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_duration = metrics.Metric(
    name="aws_lambda_duration",
    title=Localizable("Duration of Lambda functions"),
    unit=Unit.SECOND,
    color=Color.PURPLE,
)

metric_aws_lambda_duration_in_percent = metrics.Metric(
    name="aws_lambda_duration_in_percent",
    title=Localizable("Duration in percent of Lambda timeout"),
    unit=Unit.PERCENTAGE,
    color=Color.ORANGE,
)

metric_aws_lambda_invocations = metrics.Metric(
    name="aws_lambda_invocations",
    title=Localizable("Invocations"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_aws_lambda_throttles = metrics.Metric(
    name="aws_lambda_throttles",
    title=Localizable("Throttles"),
    unit=Unit.PER_SECOND,
    color=Color.DARK_YELLOW,
)

metric_aws_lambda_iterator_age = metrics.Metric(
    name="aws_lambda_iterator_age",
    title=Localizable("Iterator age"),
    unit=Unit.SECOND,
    color=Color.LIGHT_GREEN,
)

metric_aws_lambda_dead_letter_errors = metrics.Metric(
    name="aws_lambda_dead_letter_errors",
    title=Localizable("Dead letter errors"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_init_duration_absolute = metrics.Metric(
    name="aws_lambda_init_duration_absolute",
    title=Localizable("Init duration"),
    unit=Unit.SECOND,
    color=Color.BLUE,
)

metric_aws_lambda_cold_starts_in_percent = metrics.Metric(
    name="aws_lambda_cold_starts_in_percent",
    title=Localizable("Cold starts in percent"),
    unit=Unit.PERCENTAGE,
    color=Color.PURPLE,
)

metric_aws_lambda_concurrent_executions_in_percent = metrics.Metric(
    name="aws_lambda_concurrent_executions_in_percent",
    title=Localizable("Concurrent executions in percent"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_concurrent_executions = metrics.Metric(
    name="aws_lambda_concurrent_executions",
    title=Localizable("Concurrent executions"),
    unit=Unit.PER_SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_unreserved_concurrent_executions_in_percent = metrics.Metric(
    name="aws_lambda_unreserved_concurrent_executions_in_percent",
    title=Localizable("Unreserved concurrent executions in percent"),
    unit=Unit.PERCENTAGE,
    color=Color.DARK_YELLOW,
)

metric_aws_lambda_unreserved_concurrent_executions = metrics.Metric(
    name="aws_lambda_unreserved_concurrent_executions",
    title=Localizable("Unreserved concurrent executions"),
    unit=Unit.PER_SECOND,
    color=Color.DARK_YELLOW,
)

metric_aws_lambda_provisioned_concurrency_executions = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_executions",
    title=Localizable("Provisioned concurrency executions"),
    unit=Unit.PER_SECOND,
    color=Color.BLUE,
)

metric_aws_lambda_provisioned_concurrency_invocations = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_invocations",
    title=Localizable("Provisioned concurrency invocations"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_lambda_provisioned_concurrency_spillover_invocations = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_spillover_invocations",
    title=Localizable("Provisioned concurrency spillover invocations"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_aws_lambda_provisioned_concurrency_utilization = metrics.Metric(
    name="aws_lambda_provisioned_concurrency_utilization",
    title=Localizable("Provisioned concurrency utilization"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_GREEN,
)

metric_aws_lambda_code_size_in_percent = metrics.Metric(
    name="aws_lambda_code_size_in_percent",
    title=Localizable("Code Size in percent"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_code_size_absolute = metrics.Metric(
    name="aws_lambda_code_size_absolute",
    title=Localizable("Code Size"),
    unit=Unit.BYTES_IEC,
    color=Color.LIGHT_BLUE,
)

metric_aws_lambda_memory_size_in_percent = metrics.Metric(
    name="aws_lambda_memory_size_in_percent",
    title=Localizable("Memory Size in percent"),
    unit=Unit.PERCENTAGE,
    color=Color.BLUE,
)

metric_aws_lambda_memory_size_absolute = metrics.Metric(
    name="aws_lambda_memory_size_absolute",
    title=Localizable("Memory Size"),
    unit=Unit.BYTES_IEC,
    color=Color.PURPLE,
)

metric_aws_route53_child_health_check_healthy_count = metrics.Metric(
    name="aws_route53_child_health_check_healthy_count",
    title=Localizable("Health check healty count"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_route53_connection_time = metrics.Metric(
    name="aws_route53_connection_time",
    title=Localizable("Connection time"),
    unit=Unit.SECOND,
    color=Color.LIGHT_BLUE,
)

metric_aws_route53_health_check_percentage_healthy = metrics.Metric(
    name="aws_route53_health_check_percentage_healthy",
    title=Localizable("Health check percentage healty"),
    unit=Unit.PERCENTAGE,
    color=Color.PURPLE,
)

metric_aws_route53_ssl_handshake_time = metrics.Metric(
    name="aws_route53_ssl_handshake_time",
    title=Localizable("SSL handshake time"),
    unit=Unit.SECOND,
    color=Color.PURPLE,
)

metric_aws_route53_time_to_first_byte = metrics.Metric(
    name="aws_route53_time_to_first_byte",
    title=Localizable("Time to first byte"),
    unit=Unit.SECOND,
    color=Color.PURPLE,
)

metric_aws_sns_topics_standard = metrics.Metric(
    name="aws_sns_topics_standard",
    title=Localizable("Standard Topics"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_sns_topics_fifo = metrics.Metric(
    name="aws_sns_topics_fifo",
    title=Localizable("FIFO Topics"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_cloudfront_requests = metrics.Metric(
    name="aws_cloudfront_requests",
    title=Localizable("Requests"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_aws_cloudfront_total_error_rate = metrics.Metric(
    name="aws_cloudfront_total_error_rate",
    title=Localizable("Total error rate"),
    unit=Unit.PERCENTAGE,
    color=Color.YELLOW,
)

metric_aws_cloudfront_4xx_error_rate = metrics.Metric(
    name="aws_cloudfront_4xx_error_rate",
    title=Localizable("4xx error rate"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_GREEN,
)

metric_aws_cloudfront_5xx_error_rate = metrics.Metric(
    name="aws_cloudfront_5xx_error_rate",
    title=Localizable("5xx error rate"),
    unit=Unit.PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_aws_ecs_clusters = metrics.Metric(
    name="aws_ecs_clusters",
    title=Localizable("Clusters"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_aws_elasticache_nodes = metrics.Metric(
    name="aws_elasticache_nodes",
    title=Localizable("Nodes"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_aws_elasticache_parameter_groups = metrics.Metric(
    name="aws_elasticache_parameter_groups",
    title=Localizable("Parameter groups"),
    unit=Unit.COUNT,
    color=Color.LIGHT_GREEN,
)

metric_aws_elasticache_subnet_groups = metrics.Metric(
    name="aws_elasticache_subnet_groups",
    title=Localizable("Subnet groups"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)
