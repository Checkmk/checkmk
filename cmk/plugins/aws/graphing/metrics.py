#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, Localizable, metric, Unit

metric_aws_costs_unblended = metric.Metric(
    "aws_costs_unblended",
    Localizable("Unblended costs"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_glacier_number_of_vaults = metric.Metric(
    "aws_glacier_number_of_vaults",
    Localizable("Number of vaults"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_glacier_num_archives = metric.Metric(
    "aws_glacier_num_archives",
    Localizable("Number of archives"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_glacier_vault_size = metric.Metric(
    "aws_glacier_vault_size",
    Localizable("Vault size"),
    Unit.BYTES_IEC,
    Color.ORANGE,
)

metric_aws_glacier_total_vault_size = metric.Metric(
    "aws_glacier_total_vault_size",
    Localizable("Total size of all vaults"),
    Unit.BYTES_IEC,
    Color.ORANGE,
)

metric_aws_glacier_largest_vault_size = metric.Metric(
    "aws_glacier_largest_vault_size",
    Localizable("Largest vault size"),
    Unit.BYTES_IEC,
    Color.YELLOW,
)

metric_aws_num_objects = metric.Metric(
    "aws_num_objects",
    Localizable("Number of objects"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_bucket_size = metric.Metric(
    "aws_bucket_size",
    Localizable("Bucket size"),
    Unit.BYTES_IEC,
    Color.ORANGE,
)

metric_aws_largest_bucket_size = metric.Metric(
    "aws_largest_bucket_size",
    Localizable("Largest bucket size"),
    Unit.BYTES_IEC,
    Color.YELLOW,
)

metric_aws_surge_queue_length = metric.Metric(
    "aws_surge_queue_length",
    Localizable("Surge queue length"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_spillover = metric.Metric(
    "aws_spillover",
    Localizable("The rate of requests that were rejected (spillover)"),
    Unit.PER_SECOND,
    Color.LIGHT_PURPLE,
)

metric_aws_load_balancer_latency = metric.Metric(
    "aws_load_balancer_latency",
    Localizable("Load balancer latency"),
    Unit.SECOND,
    Color.YELLOW,
)

metric_aws_http_2xx_rate = metric.Metric(
    "aws_http_2xx_rate",
    Localizable("HTTP 2XX errors"),
    Unit.PER_SECOND,
    Color.BROWN,
)

metric_aws_http_2xx_perc = metric.Metric(
    "aws_http_2xx_perc",
    Localizable("Percentage of HTTP 2XX errors"),
    Unit.PERCENTAGE,
    Color.BROWN,
)

metric_aws_http_3xx_rate = metric.Metric(
    "aws_http_3xx_rate",
    Localizable("HTTP 3XX errors"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_http_3xx_perc = metric.Metric(
    "aws_http_3xx_perc",
    Localizable("Percentage of HTTP 3XX errors"),
    Unit.PERCENTAGE,
    Color.PURPLE,
)

metric_aws_http_4xx_rate = metric.Metric(
    "aws_http_4xx_rate",
    Localizable("HTTP 4XX errors"),
    Unit.PER_SECOND,
    Color.LIGHT_GREEN,
)

metric_aws_http_4xx_perc = metric.Metric(
    "aws_http_4xx_perc",
    Localizable("Percentage of HTTP 4XX errors"),
    Unit.PERCENTAGE,
    Color.LIGHT_GREEN,
)

metric_aws_http_5xx_rate = metric.Metric(
    "aws_http_5xx_rate",
    Localizable("HTTP 5XX errors"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_http_5xx_perc = metric.Metric(
    "aws_http_5xx_perc",
    Localizable("Percentage of HTTP 5XX errors"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_http_500_rate = metric.Metric(
    "aws_http_500_rate",
    Localizable("HTTP 500 errors"),
    Unit.PER_SECOND,
    Color.LIGHT_PURPLE,
)

metric_aws_http_500_perc = metric.Metric(
    "aws_http_500_perc",
    Localizable("Percentage of HTTP 500 errors"),
    Unit.PERCENTAGE,
    Color.LIGHT_PURPLE,
)

metric_aws_http_502_rate = metric.Metric(
    "aws_http_502_rate",
    Localizable("HTTP 502 errors"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_http_502_perc = metric.Metric(
    "aws_http_502_perc",
    Localizable("Percentage of HTTP 502 errors"),
    Unit.PERCENTAGE,
    Color.ORANGE,
)

metric_aws_http_503_rate = metric.Metric(
    "aws_http_503_rate",
    Localizable("HTTP 503 errors"),
    Unit.PER_SECOND,
    Color.LIGHT_ORANGE,
)

metric_aws_http_503_perc = metric.Metric(
    "aws_http_503_perc",
    Localizable("Percentage of HTTP 503 errors"),
    Unit.PERCENTAGE,
    Color.LIGHT_ORANGE,
)

metric_aws_http_504_rate = metric.Metric(
    "aws_http_504_rate",
    Localizable("HTTP 504 errors"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_http_504_perc = metric.Metric(
    "aws_http_504_perc",
    Localizable("Percentage of HTTP 504 errors"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_users_errors_rate = metric.Metric(
    "aws_lambda_users_errors_rate",
    Localizable("Lambda user errors"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_users_errors_perc = metric.Metric(
    "aws_lambda_users_errors_perc",
    Localizable("Percentage of Lambda user errors"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_overall_hosts_health_perc = metric.Metric(
    "aws_overall_hosts_health_perc",
    Localizable("Proportion of healthy host"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_backend_connection_errors_rate = metric.Metric(
    "aws_backend_connection_errors_rate",
    Localizable("Backend connection errors"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_burst_balance = metric.Metric(
    "aws_burst_balance",
    Localizable("Burst Balance"),
    Unit.PERCENTAGE,
    Color.PURPLE,
)

metric_aws_cpu_credit_balance = metric.Metric(
    "aws_cpu_credit_balance",
    Localizable("CPU Credit Balance"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_rds_bin_log_disk_usage = metric.Metric(
    "aws_rds_bin_log_disk_usage",
    Localizable("Bin Log Disk Usage"),
    Unit.PERCENTAGE,
    Color.PURPLE,
)

metric_aws_rds_transaction_logs_disk_usage = metric.Metric(
    "aws_rds_transaction_logs_disk_usage",
    Localizable("Transaction Logs Disk Usage"),
    Unit.PERCENTAGE,
    Color.PURPLE,
)

metric_aws_rds_replication_slot_disk_usage = metric.Metric(
    "aws_rds_replication_slot_disk_usage",
    Localizable("Replication Slot Disk Usage"),
    Unit.PERCENTAGE,
    Color.LIGHT_PURPLE,
)

metric_aws_rds_replica_lag = metric.Metric(
    "aws_rds_replica_lag",
    Localizable("Replica Lag"),
    Unit.SECOND,
    Color.ORANGE,
)

metric_aws_rds_oldest_replication_slot_lag = metric.Metric(
    "aws_rds_oldest_replication_slot_lag",
    Localizable("Oldest Replication Slot Lag Size"),
    Unit.BYTES_IEC,
    Color.ORANGE,
)

metric_aws_rds_connections = metric.Metric(
    "aws_rds_connections",
    Localizable("Connections in use"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_request_latency = metric.Metric(
    "aws_request_latency",
    Localizable("Request latency"),
    Unit.SECOND,
    Color.YELLOW,
)

metric_aws_ec2_vpc_elastic_ip_addresses = metric.Metric(
    "aws_ec2_vpc_elastic_ip_addresses",
    Localizable("VPC Elastic IP Addresses"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_elastic_ip_addresses = metric.Metric(
    "aws_ec2_elastic_ip_addresses",
    Localizable("Elastic IP Addresses"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_spot_inst_requests = metric.Metric(
    "aws_ec2_spot_inst_requests",
    Localizable("Spot Instance Requests"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_ec2_active_spot_fleet_requests = metric.Metric(
    "aws_ec2_active_spot_fleet_requests",
    Localizable("Active Spot Fleet Requests"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_spot_fleet_total_target_capacity = metric.Metric(
    "aws_ec2_spot_fleet_total_target_capacity",
    Localizable("Spot Fleet Requests Total Target Capacity"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_total = metric.Metric(
    "aws_ec2_running_ondemand_instances_total",
    Localizable("Total running On-Demand Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_a1_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_a1.2xlarge",
    Localizable("Total running On-Demand a1.2xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_a1.4xlarge",
    Localizable("Total running On-Demand a1.4xlarge Instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_a1_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_a1.large",
    Localizable("Total running On-Demand a1.large Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_a1_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_a1.medium",
    Localizable("Total running On-Demand a1.medium Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_a1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_a1.metal",
    Localizable("Total running On-Demand a1.metal Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_a1_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_a1.xlarge",
    Localizable("Total running On-Demand a1.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c1_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_c1.medium",
    Localizable("Total running On-Demand c1.medium Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c1_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c1.xlarge",
    Localizable("Total running On-Demand c1.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c3.2xlarge",
    Localizable("Total running On-Demand c3.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c3_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c3.4xlarge",
    Localizable("Total running On-Demand c3.4xlarge Instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c3_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c3.8xlarge",
    Localizable("Total running On-Demand c3.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c3.large",
    Localizable("Total running On-Demand c3.large Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c3_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c3.xlarge",
    Localizable("Total running On-Demand c3.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c4.2xlarge",
    Localizable("Total running On-Demand c4.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c4_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c4.4xlarge",
    Localizable("Total running On-Demand c4.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c4_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c4.8xlarge",
    Localizable("Total running On-Demand c4.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c4_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c4.large",
    Localizable("Total running On-Demand c4.large Instances"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c4.xlarge",
    Localizable("Total running On-Demand c4.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.12xlarge",
    Localizable("Total running On-Demand c5.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_18xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.18xlarge",
    Localizable("Total running On-Demand c5.18xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.24xlarge",
    Localizable("Total running On-Demand c5.24xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.2xlarge",
    Localizable("Total running On-Demand c5.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.4xlarge",
    Localizable("Total running On-Demand c5.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5_9xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.9xlarge",
    Localizable("Total running On-Demand c5.9xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.large",
    Localizable("Total running On-Demand c5.large Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.metal",
    Localizable("Total running On-Demand c5.metal Instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5.xlarge",
    Localizable("Total running On-Demand c5.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5a_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.12xlarge",
    Localizable("Total running On-Demand c5a.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5a_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.16xlarge",
    Localizable("Total running On-Demand c5a.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5a_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.24xlarge",
    Localizable("Total running On-Demand c5a.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5a_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.2xlarge",
    Localizable("Total running On-Demand c5a.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5a_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.4xlarge",
    Localizable("Total running On-Demand c5a.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5a_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.8xlarge",
    Localizable("Total running On-Demand c5a.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5a_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.large",
    Localizable("Total running On-Demand c5a.large Instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5a_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5a.xlarge",
    Localizable("Total running On-Demand c5a.xlarge Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.12xlarge",
    Localizable("Total running On-Demand c5ad.12xlarge Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.16xlarge",
    Localizable("Total running On-Demand c5ad.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.24xlarge",
    Localizable("Total running On-Demand c5ad.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5ad_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.2xlarge",
    Localizable("Total running On-Demand c5ad.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.4xlarge",
    Localizable("Total running On-Demand c5ad.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.8xlarge",
    Localizable("Total running On-Demand c5ad.8xlarge Instances"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5ad_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.large",
    Localizable("Total running On-Demand c5ad.large Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5ad_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5ad.xlarge",
    Localizable("Total running On-Demand c5ad.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.12xlarge",
    Localizable("Total running On-Demand c5d.12xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_18xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.18xlarge",
    Localizable("Total running On-Demand c5d.18xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c5d_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.24xlarge",
    Localizable("Total running On-Demand c5d.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5d_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.2xlarge",
    Localizable("Total running On-Demand c5d.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.4xlarge",
    Localizable("Total running On-Demand c5d.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5d_9xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.9xlarge",
    Localizable("Total running On-Demand c5d.9xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5d_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.large",
    Localizable("Total running On-Demand c5d.large Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5d_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.metal",
    Localizable("Total running On-Demand c5d.metal Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5d_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5d.xlarge",
    Localizable("Total running On-Demand c5d.xlarge Instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c5n_18xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.18xlarge",
    Localizable("Total running On-Demand c5n.18xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c5n_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.2xlarge",
    Localizable("Total running On-Demand c5n.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.4xlarge",
    Localizable("Total running On-Demand c5n.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c5n_9xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.9xlarge",
    Localizable("Total running On-Demand c5n.9xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c5n_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.large",
    Localizable("Total running On-Demand c5n.large Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c5n_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.metal",
    Localizable("Total running On-Demand c5n.metal Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c5n_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c5n.xlarge",
    Localizable("Total running On-Demand c5n.xlarge Instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.12xlarge",
    Localizable("Total running On-Demand c6g.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.16xlarge",
    Localizable("Total running On-Demand c6g.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.2xlarge",
    Localizable("Total running On-Demand c6g.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6g_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.4xlarge",
    Localizable("Total running On-Demand c6g.4xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6g_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.8xlarge",
    Localizable("Total running On-Demand c6g.8xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6g_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.large",
    Localizable("Total running On-Demand c6g.large Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6g_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.medium",
    Localizable("Total running On-Demand c6g.medium Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6g_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.metal",
    Localizable("Total running On-Demand c6g.metal Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6g_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6g.xlarge",
    Localizable("Total running On-Demand c6g.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.12xlarge",
    Localizable("Total running On-Demand c6gd.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gd_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.16xlarge",
    Localizable("Total running On-Demand c6gd.16xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gd_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.2xlarge",
    Localizable("Total running On-Demand c6gd.2xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.4xlarge",
    Localizable("Total running On-Demand c6gd.4xlarge Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gd_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.8xlarge",
    Localizable("Total running On-Demand c6gd.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gd_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.large",
    Localizable("Total running On-Demand c6gd.large Instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gd_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.medium",
    Localizable("Total running On-Demand c6gd.medium Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gd_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.metal",
    Localizable("Total running On-Demand c6gd.metal Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gd_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gd.xlarge",
    Localizable("Total running On-Demand c6gd.xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.12xlarge",
    Localizable("Total running On-Demand c6gn.12xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.16xlarge",
    Localizable("Total running On-Demand c6gn.16xlarge Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.2xlarge",
    Localizable("Total running On-Demand c6gn.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c6gn_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.4xlarge",
    Localizable("Total running On-Demand c6gn.4xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c6gn_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.8xlarge",
    Localizable("Total running On-Demand c6gn.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_c6gn_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.large",
    Localizable("Total running On-Demand c6gn.large Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_c6gn_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.medium",
    Localizable("Total running On-Demand c6gn.medium Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_c6gn_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_c6gn.xlarge",
    Localizable("Total running On-Demand c6gn.xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_cc1_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_cc1.4xlarge",
    Localizable("Total running On-Demand cc1.4xlarge Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_cc2_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_cc2.8xlarge",
    Localizable("Total running On-Demand cc2.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_cg1_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_cg1.4xlarge",
    Localizable("Total running On-Demand cg1.4xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_cr1_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_cr1.8xlarge",
    Localizable("Total running On-Demand cr1.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d2_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d2.2xlarge",
    Localizable("Total running On-Demand d2.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_d2_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d2.4xlarge",
    Localizable("Total running On-Demand d2.4xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d2_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d2.8xlarge",
    Localizable("Total running On-Demand d2.8xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d2_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d2.xlarge",
    Localizable("Total running On-Demand d2.xlarge Instances"),
    Unit.COUNT,
    Color.BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3.2xlarge",
    Localizable("Total running On-Demand d3.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3.4xlarge",
    Localizable("Total running On-Demand d3.4xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3.8xlarge",
    Localizable("Total running On-Demand d3.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3.xlarge",
    Localizable("Total running On-Demand d3.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_d3en_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3en.12xlarge",
    Localizable("Total running On-Demand d3en.12xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_d3en_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3en.2xlarge",
    Localizable("Total running On-Demand d3en.2xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_d3en_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3en.4xlarge",
    Localizable("Total running On-Demand d3en.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_d3en_6xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3en.6xlarge",
    Localizable("Total running On-Demand d3en.6xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_d3en_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3en.8xlarge",
    Localizable("Total running On-Demand d3en.8xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_d3en_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_d3en.xlarge",
    Localizable("Total running On-Demand d3en.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_f1_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_f1.16xlarge",
    Localizable("Total running On-Demand f1.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_f1_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_f1.2xlarge",
    Localizable("Total running On-Demand f1.2xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_f1_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_f1.4xlarge",
    Localizable("Total running On-Demand f1.4xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g2_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g2.2xlarge",
    Localizable("Total running On-Demand g2.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g2_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g2.8xlarge",
    Localizable("Total running On-Demand g2.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g3_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g3.16xlarge",
    Localizable("Total running On-Demand g3.16xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g3_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g3.4xlarge",
    Localizable("Total running On-Demand g3.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g3_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g3.8xlarge",
    Localizable("Total running On-Demand g3.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g3s_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g3s.xlarge",
    Localizable("Total running On-Demand g3s.xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4ad_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4ad.16xlarge",
    Localizable("Total running On-Demand g4ad.16xlarge Instances"),
    Unit.COUNT,
    Color.GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4ad_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4ad.2xlarge",
    Localizable("Total running On-Demand g4ad.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4ad.4xlarge",
    Localizable("Total running On-Demand g4ad.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4ad_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4ad.8xlarge",
    Localizable("Total running On-Demand g4ad.8xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4ad_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4ad.xlarge",
    Localizable("Total running On-Demand g4ad.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.12xlarge",
    Localizable("Total running On-Demand g4dn.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_g4dn_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.16xlarge",
    Localizable("Total running On-Demand g4dn.16xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_g4dn_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.2xlarge",
    Localizable("Total running On-Demand g4dn.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_g4dn_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.4xlarge",
    Localizable("Total running On-Demand g4dn.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.8xlarge",
    Localizable("Total running On-Demand g4dn.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g4dn_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.metal",
    Localizable("Total running On-Demand g4dn.metal Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_g4dn_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_g4dn.xlarge",
    Localizable("Total running On-Demand g4dn.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_h1.16xlarge",
    Localizable("Total running On-Demand h1.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_h1_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_h1.2xlarge",
    Localizable("Total running On-Demand h1.2xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_h1_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_h1.4xlarge",
    Localizable("Total running On-Demand h1.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_h1_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_h1.8xlarge",
    Localizable("Total running On-Demand h1.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_hi1_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_hi1.4xlarge",
    Localizable("Total running On-Demand hi1.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_hs1_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_hs1.8xlarge",
    Localizable("Total running On-Demand hs1.8xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i2_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i2.2xlarge",
    Localizable("Total running On-Demand i2.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i2_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i2.4xlarge",
    Localizable("Total running On-Demand i2.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i2_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i2.8xlarge",
    Localizable("Total running On-Demand i2.8xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i2_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i2.xlarge",
    Localizable("Total running On-Demand i2.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.16xlarge",
    Localizable("Total running On-Demand i3.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.2xlarge",
    Localizable("Total running On-Demand i3.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.4xlarge",
    Localizable("Total running On-Demand i3.4xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.8xlarge",
    Localizable("Total running On-Demand i3.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.large",
    Localizable("Total running On-Demand i3.large Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.metal",
    Localizable("Total running On-Demand i3.metal Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3.xlarge",
    Localizable("Total running On-Demand i3.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.12xlarge",
    Localizable("Total running On-Demand i3en.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_i3en_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.24xlarge",
    Localizable("Total running On-Demand i3en.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i3en_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.2xlarge",
    Localizable("Total running On-Demand i3en.2xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_i3en_3xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.3xlarge",
    Localizable("Total running On-Demand i3en.3xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_6xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.6xlarge",
    Localizable("Total running On-Demand i3en.6xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_i3en_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.large",
    Localizable("Total running On-Demand i3en.large Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_i3en_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.metal",
    Localizable("Total running On-Demand i3en.metal Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_i3en_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_i3en.xlarge",
    Localizable("Total running On-Demand i3en.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_inf1_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_inf1.24xlarge",
    Localizable("Total running On-Demand inf1.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_inf1_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_inf1.2xlarge",
    Localizable("Total running On-Demand inf1.2xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_inf1_6xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_inf1.6xlarge",
    Localizable("Total running On-Demand inf1.6xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_inf1_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_inf1.xlarge",
    Localizable("Total running On-Demand inf1.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m1_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m1.large",
    Localizable("Total running On-Demand m1.large Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m1_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_m1.medium",
    Localizable("Total running On-Demand m1.medium Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m1_small = metric.Metric(
    "aws_ec2_running_ondemand_instances_m1.small",
    Localizable("Total running On-Demand m1.small Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m1_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m1.xlarge",
    Localizable("Total running On-Demand m1.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m2_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m2.2xlarge",
    Localizable("Total running On-Demand m2.2xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m2_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m2.4xlarge",
    Localizable("Total running On-Demand m2.4xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m2_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m2.xlarge",
    Localizable("Total running On-Demand m2.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m3.2xlarge",
    Localizable("Total running On-Demand m3.2xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m3_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m3.large",
    Localizable("Total running On-Demand m3.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m3_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_m3.medium",
    Localizable("Total running On-Demand m3.medium Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m3_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m3.xlarge",
    Localizable("Total running On-Demand m3.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m4_10xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m4.10xlarge",
    Localizable("Total running On-Demand m4.10xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m4_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m4.16xlarge",
    Localizable("Total running On-Demand m4.16xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m4_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m4.2xlarge",
    Localizable("Total running On-Demand m4.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m4_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m4.4xlarge",
    Localizable("Total running On-Demand m4.4xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m4_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m4.large",
    Localizable("Total running On-Demand m4.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m4_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m4.xlarge",
    Localizable("Total running On-Demand m4.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.12xlarge",
    Localizable("Total running On-Demand m5.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.16xlarge",
    Localizable("Total running On-Demand m5.16xlarge Instances"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.24xlarge",
    Localizable("Total running On-Demand m5.24xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.2xlarge",
    Localizable("Total running On-Demand m5.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.4xlarge",
    Localizable("Total running On-Demand m5.4xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.8xlarge",
    Localizable("Total running On-Demand m5.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.large",
    Localizable("Total running On-Demand m5.large Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.metal",
    Localizable("Total running On-Demand m5.metal Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5.xlarge",
    Localizable("Total running On-Demand m5.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.12xlarge",
    Localizable("Total running On-Demand m5a.12xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.16xlarge",
    Localizable("Total running On-Demand m5a.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5a_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.24xlarge",
    Localizable("Total running On-Demand m5a.24xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5a_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.2xlarge",
    Localizable("Total running On-Demand m5a.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5a_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.4xlarge",
    Localizable("Total running On-Demand m5a.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5a_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.8xlarge",
    Localizable("Total running On-Demand m5a.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5a_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.large",
    Localizable("Total running On-Demand m5a.large Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5a_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5a.xlarge",
    Localizable("Total running On-Demand m5a.xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.12xlarge",
    Localizable("Total running On-Demand m5ad.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.16xlarge",
    Localizable("Total running On-Demand m5ad.16xlarge Instances"),
    Unit.COUNT,
    Color.RED,
)

metric_aws_ec2_running_ondemand_instances_m5ad_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.24xlarge",
    Localizable("Total running On-Demand m5ad.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5ad_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.2xlarge",
    Localizable("Total running On-Demand m5ad.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5ad_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.4xlarge",
    Localizable("Total running On-Demand m5ad.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5ad_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.8xlarge",
    Localizable("Total running On-Demand m5ad.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5ad_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.large",
    Localizable("Total running On-Demand m5ad.large Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5ad_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5ad.xlarge",
    Localizable("Total running On-Demand m5ad.xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.12xlarge",
    Localizable("Total running On-Demand m5d.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5d_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.16xlarge",
    Localizable("Total running On-Demand m5d.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5d_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.24xlarge",
    Localizable("Total running On-Demand m5d.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5d_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.2xlarge",
    Localizable("Total running On-Demand m5d.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5d_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.4xlarge",
    Localizable("Total running On-Demand m5d.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5d_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.8xlarge",
    Localizable("Total running On-Demand m5d.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.large",
    Localizable("Total running On-Demand m5d.large Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5d_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.metal",
    Localizable("Total running On-Demand m5d.metal Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5d_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5d.xlarge",
    Localizable("Total running On-Demand m5d.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.12xlarge",
    Localizable("Total running On-Demand m5dn.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.16xlarge",
    Localizable("Total running On-Demand m5dn.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5dn_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.24xlarge",
    Localizable("Total running On-Demand m5dn.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.2xlarge",
    Localizable("Total running On-Demand m5dn.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.4xlarge",
    Localizable("Total running On-Demand m5dn.4xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5dn_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.8xlarge",
    Localizable("Total running On-Demand m5dn.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5dn_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.large",
    Localizable("Total running On-Demand m5dn.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5dn_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.metal",
    Localizable("Total running On-Demand m5dn.metal Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5dn_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5dn.xlarge",
    Localizable("Total running On-Demand m5dn.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_m5n_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.12xlarge",
    Localizable("Total running On-Demand m5n.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.16xlarge",
    Localizable("Total running On-Demand m5n.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.24xlarge",
    Localizable("Total running On-Demand m5n.24xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5n_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.2xlarge",
    Localizable("Total running On-Demand m5n.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5n_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.4xlarge",
    Localizable("Total running On-Demand m5n.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5n_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.8xlarge",
    Localizable("Total running On-Demand m5n.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5n_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.large",
    Localizable("Total running On-Demand m5n.large Instances"),
    Unit.COUNT,
    Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5n_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.metal",
    Localizable("Total running On-Demand m5n.metal Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5n_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5n.xlarge",
    Localizable("Total running On-Demand m5n.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.12xlarge",
    Localizable("Total running On-Demand m5zn.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m5zn_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.2xlarge",
    Localizable("Total running On-Demand m5zn.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m5zn_3xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.3xlarge",
    Localizable("Total running On-Demand m5zn.3xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_6xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.6xlarge",
    Localizable("Total running On-Demand m5zn.6xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.large",
    Localizable("Total running On-Demand m5zn.large Instances"),
    Unit.COUNT,
    Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m5zn_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.metal",
    Localizable("Total running On-Demand m5zn.metal Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m5zn_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m5zn.xlarge",
    Localizable("Total running On-Demand m5zn.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.12xlarge",
    Localizable("Total running On-Demand m6g.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.16xlarge",
    Localizable("Total running On-Demand m6g.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6g_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.2xlarge",
    Localizable("Total running On-Demand m6g.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6g_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.4xlarge",
    Localizable("Total running On-Demand m6g.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6g_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.8xlarge",
    Localizable("Total running On-Demand m6g.8xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6g_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.large",
    Localizable("Total running On-Demand m6g.large Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6g_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.medium",
    Localizable("Total running On-Demand m6g.medium Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.metal",
    Localizable("Total running On-Demand m6g.metal Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6g_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6g.xlarge",
    Localizable("Total running On-Demand m6g.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6gd_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.12xlarge",
    Localizable("Total running On-Demand m6gd.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.16xlarge",
    Localizable("Total running On-Demand m6gd.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6gd_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.2xlarge",
    Localizable("Total running On-Demand m6gd.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.4xlarge",
    Localizable("Total running On-Demand m6gd.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6gd_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.8xlarge",
    Localizable("Total running On-Demand m6gd.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6gd_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.large",
    Localizable("Total running On-Demand m6gd.large Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6gd_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.medium",
    Localizable("Total running On-Demand m6gd.medium Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6gd_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.metal",
    Localizable("Total running On-Demand m6gd.metal Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6gd_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6gd.xlarge",
    Localizable("Total running On-Demand m6gd.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6i_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.12xlarge",
    Localizable("Total running On-Demand m6i.12xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6i_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.16xlarge",
    Localizable("Total running On-Demand m6i.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_m6i_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.24xlarge",
    Localizable("Total running On-Demand m6i.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6i_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.2xlarge",
    Localizable("Total running On-Demand m6i.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_m6i_32xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.32xlarge",
    Localizable("Total running On-Demand m6i.32xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_m6i_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.4xlarge",
    Localizable("Total running On-Demand m6i.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_m6i_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.8xlarge",
    Localizable("Total running On-Demand m6i.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_m6i_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.large",
    Localizable("Total running On-Demand m6i.large Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_m6i_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_m6i.xlarge",
    Localizable("Total running On-Demand m6i.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_mac1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_mac1.metal",
    Localizable("Total running On-Demand mac1.metal Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p2_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p2.16xlarge",
    Localizable("Total running On-Demand p2.16xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p2_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p2.8xlarge",
    Localizable("Total running On-Demand p2.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_p2_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p2.xlarge",
    Localizable("Total running On-Demand p2.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_p3_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p3.16xlarge",
    Localizable("Total running On-Demand p3.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_p3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p3.2xlarge",
    Localizable("Total running On-Demand p3.2xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_p3_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p3.8xlarge",
    Localizable("Total running On-Demand p3.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_p3dn_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p3dn.24xlarge",
    Localizable("Total running On-Demand p3dn.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_p4d_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_p4d.24xlarge",
    Localizable("Total running On-Demand p4d.24xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r3.2xlarge",
    Localizable("Total running On-Demand r3.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r3_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r3.4xlarge",
    Localizable("Total running On-Demand r3.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r3_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r3.8xlarge",
    Localizable("Total running On-Demand r3.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r3_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r3.large",
    Localizable("Total running On-Demand r3.large Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r3_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r3.xlarge",
    Localizable("Total running On-Demand r3.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r4_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r4.16xlarge",
    Localizable("Total running On-Demand r4.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r4_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r4.2xlarge",
    Localizable("Total running On-Demand r4.2xlarge Instances"),
    Unit.COUNT,
    Color.LIGHT_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r4_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r4.4xlarge",
    Localizable("Total running On-Demand r4.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r4_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r4.8xlarge",
    Localizable("Total running On-Demand r4.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r4_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r4.large",
    Localizable("Total running On-Demand r4.large Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r4_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r4.xlarge",
    Localizable("Total running On-Demand r4.xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.12xlarge",
    Localizable("Total running On-Demand r5.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.16xlarge",
    Localizable("Total running On-Demand r5.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.24xlarge",
    Localizable("Total running On-Demand r5.24xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.2xlarge",
    Localizable("Total running On-Demand r5.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.4xlarge",
    Localizable("Total running On-Demand r5.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.8xlarge",
    Localizable("Total running On-Demand r5.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.large",
    Localizable("Total running On-Demand r5.large Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.metal",
    Localizable("Total running On-Demand r5.metal Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5.xlarge",
    Localizable("Total running On-Demand r5.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.12xlarge",
    Localizable("Total running On-Demand r5a.12xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.16xlarge",
    Localizable("Total running On-Demand r5a.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5a_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.24xlarge",
    Localizable("Total running On-Demand r5a.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5a_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.2xlarge",
    Localizable("Total running On-Demand r5a.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5a_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.4xlarge",
    Localizable("Total running On-Demand r5a.4xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5a_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.8xlarge",
    Localizable("Total running On-Demand r5a.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5a_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.large",
    Localizable("Total running On-Demand r5a.large Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5a_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5a.xlarge",
    Localizable("Total running On-Demand r5a.xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.12xlarge",
    Localizable("Total running On-Demand r5ad.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5ad_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.16xlarge",
    Localizable("Total running On-Demand r5ad.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5ad_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.24xlarge",
    Localizable("Total running On-Demand r5ad.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5ad_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.2xlarge",
    Localizable("Total running On-Demand r5ad.2xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5ad_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.4xlarge",
    Localizable("Total running On-Demand r5ad.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5ad_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.8xlarge",
    Localizable("Total running On-Demand r5ad.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.large",
    Localizable("Total running On-Demand r5ad.large Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5ad_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5ad.xlarge",
    Localizable("Total running On-Demand r5ad.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.12xlarge",
    Localizable("Total running On-Demand r5b.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.16xlarge",
    Localizable("Total running On-Demand r5b.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5b_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.24xlarge",
    Localizable("Total running On-Demand r5b.24xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5b_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.2xlarge",
    Localizable("Total running On-Demand r5b.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5b_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.4xlarge",
    Localizable("Total running On-Demand r5b.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.8xlarge",
    Localizable("Total running On-Demand r5b.8xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5b_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.large",
    Localizable("Total running On-Demand r5b.large Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5b_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.metal",
    Localizable("Total running On-Demand r5b.metal Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5b_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5b.xlarge",
    Localizable("Total running On-Demand r5b.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.12xlarge",
    Localizable("Total running On-Demand r5d.12xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.16xlarge",
    Localizable("Total running On-Demand r5d.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5d_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.24xlarge",
    Localizable("Total running On-Demand r5d.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.2xlarge",
    Localizable("Total running On-Demand r5d.2xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5d_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.4xlarge",
    Localizable("Total running On-Demand r5d.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5d_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.8xlarge",
    Localizable("Total running On-Demand r5d.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5d_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.large",
    Localizable("Total running On-Demand r5d.large Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5d_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.metal",
    Localizable("Total running On-Demand r5d.metal Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5d_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5d.xlarge",
    Localizable("Total running On-Demand r5d.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.12xlarge",
    Localizable("Total running On-Demand r5dn.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.16xlarge",
    Localizable("Total running On-Demand r5dn.16xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.24xlarge",
    Localizable("Total running On-Demand r5dn.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5dn_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.2xlarge",
    Localizable("Total running On-Demand r5dn.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5dn_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.4xlarge",
    Localizable("Total running On-Demand r5dn.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.8xlarge",
    Localizable("Total running On-Demand r5dn.8xlarge Instances"),
    Unit.COUNT,
    Color.BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5dn_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.large",
    Localizable("Total running On-Demand r5dn.large Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5dn_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.metal",
    Localizable("Total running On-Demand r5dn.metal Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5dn_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5dn.xlarge",
    Localizable("Total running On-Demand r5dn.xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.12xlarge",
    Localizable("Total running On-Demand r5n.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5n_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.16xlarge",
    Localizable("Total running On-Demand r5n.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r5n_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.24xlarge",
    Localizable("Total running On-Demand r5n.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r5n_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.2xlarge",
    Localizable("Total running On-Demand r5n.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r5n_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.4xlarge",
    Localizable("Total running On-Demand r5n.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r5n_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.8xlarge",
    Localizable("Total running On-Demand r5n.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.large",
    Localizable("Total running On-Demand r5n.large Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r5n_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.metal",
    Localizable("Total running On-Demand r5n.metal Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r5n_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r5n.xlarge",
    Localizable("Total running On-Demand r5n.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.12xlarge",
    Localizable("Total running On-Demand r6g.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.16xlarge",
    Localizable("Total running On-Demand r6g.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6g_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.2xlarge",
    Localizable("Total running On-Demand r6g.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6g_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.4xlarge",
    Localizable("Total running On-Demand r6g.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.8xlarge",
    Localizable("Total running On-Demand r6g.8xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6g_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.large",
    Localizable("Total running On-Demand r6g.large Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6g_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.medium",
    Localizable("Total running On-Demand r6g.medium Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6g_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.metal",
    Localizable("Total running On-Demand r6g.metal Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6g_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6g.xlarge",
    Localizable("Total running On-Demand r6g.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.12xlarge",
    Localizable("Total running On-Demand r6gd.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.16xlarge",
    Localizable("Total running On-Demand r6gd.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.2xlarge",
    Localizable("Total running On-Demand r6gd.2xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_r6gd_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.4xlarge",
    Localizable("Total running On-Demand r6gd.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_r6gd_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.8xlarge",
    Localizable("Total running On-Demand r6gd.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.large",
    Localizable("Total running On-Demand r6gd.large Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.medium",
    Localizable("Total running On-Demand r6gd.medium Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_r6gd_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.metal",
    Localizable("Total running On-Demand r6gd.metal Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_r6gd_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_r6gd.xlarge",
    Localizable("Total running On-Demand r6gd.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t1_micro = metric.Metric(
    "aws_ec2_running_ondemand_instances_t1.micro",
    Localizable("Total running On-Demand t1.micro Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.2xlarge",
    Localizable("Total running On-Demand t2.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t2_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.large",
    Localizable("Total running On-Demand t2.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t2_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.medium",
    Localizable("Total running On-Demand t2.medium Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t2_micro = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.micro",
    Localizable("Total running On-Demand t2.micro Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t2_nano = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.nano",
    Localizable("Total running On-Demand t2.nano Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t2_small = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.small",
    Localizable("Total running On-Demand t2.small Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t2_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t2.xlarge",
    Localizable("Total running On-Demand t2.xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.2xlarge",
    Localizable("Total running On-Demand t3.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.large",
    Localizable("Total running On-Demand t3.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.medium",
    Localizable("Total running On-Demand t3.medium Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3_micro = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.micro",
    Localizable("Total running On-Demand t3.micro Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3_nano = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.nano",
    Localizable("Total running On-Demand t3.nano Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3_small = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.small",
    Localizable("Total running On-Demand t3.small Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3.xlarge",
    Localizable("Total running On-Demand t3.xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.2xlarge",
    Localizable("Total running On-Demand t3a.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t3a_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.large",
    Localizable("Total running On-Demand t3a.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t3a_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.medium",
    Localizable("Total running On-Demand t3a.medium Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t3a_micro = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.micro",
    Localizable("Total running On-Demand t3a.micro Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t3a_nano = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.nano",
    Localizable("Total running On-Demand t3a.nano Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t3a_small = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.small",
    Localizable("Total running On-Demand t3a.small Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_t3a_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t3a.xlarge",
    Localizable("Total running On-Demand t3a.xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.2xlarge",
    Localizable("Total running On-Demand t4g.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_t4g_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.large",
    Localizable("Total running On-Demand t4g.large Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_t4g_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.medium",
    Localizable("Total running On-Demand t4g.medium Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_t4g_micro = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.micro",
    Localizable("Total running On-Demand t4g.micro Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_t4g_nano = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.nano",
    Localizable("Total running On-Demand t4g.nano Instances"),
    Unit.COUNT,
    Color.DARK_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_t4g_small = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.small",
    Localizable("Total running On-Demand t4g.small Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_t4g_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_t4g.xlarge",
    Localizable("Total running On-Demand t4g.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_12tb1_112xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-12tb1.112xlarge",
    Localizable("Total running On-Demand u-12tb1.112xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_12tb1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-12tb1.metal",
    Localizable("Total running On-Demand u-12tb1.metal Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_u_18tb1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-18tb1.metal",
    Localizable("Total running On-Demand u-18tb1.metal Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_u_24tb1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-24tb1.metal",
    Localizable("Total running On-Demand u-24tb1.metal Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_112xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-6tb1.112xlarge",
    Localizable("Total running On-Demand u-6tb1.112xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_56xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-6tb1.56xlarge",
    Localizable("Total running On-Demand u-6tb1.56xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_6tb1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-6tb1.metal",
    Localizable("Total running On-Demand u-6tb1.metal Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_u_9tb1_112xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-9tb1.112xlarge",
    Localizable("Total running On-Demand u-9tb1.112xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_u_9tb1_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_u-9tb1.metal",
    Localizable("Total running On-Demand u-9tb1.metal Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_vt1_24xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_vt1.24xlarge",
    Localizable("Total running On-Demand vt1.24xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_vt1_3xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_vt1.3xlarge",
    Localizable("Total running On-Demand vt1.3xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_vt1_6xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_vt1.6xlarge",
    Localizable("Total running On-Demand vt1.6xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1.16xlarge",
    Localizable("Total running On-Demand x1.16xlarge Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1_32xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1.32xlarge",
    Localizable("Total running On-Demand x1.32xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x1e_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1e.16xlarge",
    Localizable("Total running On-Demand x1e.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1e.2xlarge",
    Localizable("Total running On-Demand x1e.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x1e_32xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1e.32xlarge",
    Localizable("Total running On-Demand x1e.32xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x1e_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1e.4xlarge",
    Localizable("Total running On-Demand x1e.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x1e_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1e.8xlarge",
    Localizable("Total running On-Demand x1e.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x1e_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x1e.xlarge",
    Localizable("Total running On-Demand x1e.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.12xlarge",
    Localizable("Total running On-Demand x2gd.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_16xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.16xlarge",
    Localizable("Total running On-Demand x2gd.16xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.2xlarge",
    Localizable("Total running On-Demand x2gd.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_4xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.4xlarge",
    Localizable("Total running On-Demand x2gd.4xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_x2gd_8xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.8xlarge",
    Localizable("Total running On-Demand x2gd.8xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_x2gd_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.large",
    Localizable("Total running On-Demand x2gd.large Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_x2gd_medium = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.medium",
    Localizable("Total running On-Demand x2gd.medium Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.metal",
    Localizable("Total running On-Demand x2gd.metal Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_x2gd_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_x2gd.xlarge",
    Localizable("Total running On-Demand x2gd.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_12xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.12xlarge",
    Localizable("Total running On-Demand z1d.12xlarge Instances"),
    Unit.COUNT,
    Color.DARK_GREEN,
)

metric_aws_ec2_running_ondemand_instances_z1d_2xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.2xlarge",
    Localizable("Total running On-Demand z1d.2xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

metric_aws_ec2_running_ondemand_instances_z1d_3xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.3xlarge",
    Localizable("Total running On-Demand z1d.3xlarge Instances"),
    Unit.COUNT,
    Color.DARK_BROWN,
)

metric_aws_ec2_running_ondemand_instances_z1d_6xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.6xlarge",
    Localizable("Total running On-Demand z1d.6xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_z1d_large = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.large",
    Localizable("Total running On-Demand z1d.large Instances"),
    Unit.COUNT,
    Color.GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_metal = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.metal",
    Localizable("Total running On-Demand z1d.metal Instances"),
    Unit.COUNT,
    Color.DARK_GRAY,
)

metric_aws_ec2_running_ondemand_instances_z1d_xlarge = metric.Metric(
    "aws_ec2_running_ondemand_instances_z1d.xlarge",
    Localizable("Total running On-Demand z1d.xlarge Instances"),
    Unit.COUNT,
    Color.DARK_RED,
)

metric_aws_ec2_running_ondemand_instances_f_vcpu = metric.Metric(
    "aws_ec2_running_ondemand_instances_f_vcpu",
    Localizable("Total Localizable('Running On-Demand F instances') vCPUs"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_g_vcpu = metric.Metric(
    "aws_ec2_running_ondemand_instances_g_vcpu",
    Localizable("Total Localizable('Running On-Demand G instances') vCPUs"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_i_vcpu = metric.Metric(
    "aws_ec2_running_ondemand_instances_i_vcpu",
    Localizable("Total Localizable('Running On-Demand Inf instances') vCPUs"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_p_vcpu = metric.Metric(
    "aws_ec2_running_ondemand_instances_p_vcpu",
    Localizable("Total Localizable('Running On-Demand P instances') vCPUs"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_x_vcpu = metric.Metric(
    "aws_ec2_running_ondemand_instances_x_vcpu",
    Localizable("Total Localizable('Running On-Demand X instances') vCPUs"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances___vcpu = metric.Metric(
    "aws_ec2_running_ondemand_instances___vcpu",
    Localizable(
        "Total Localizable('Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances') vCPUs"
    ),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_consumed_lcus = metric.Metric(
    "aws_consumed_lcus",
    Localizable("Consumed Load Balancer Capacity Units"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_active_connections = metric.Metric(
    "aws_active_connections",
    Localizable("Active Connections"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_active_tls_connections = metric.Metric(
    "aws_active_tls_connections",
    Localizable("Active TLS Connections"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_new_connections = metric.Metric(
    "aws_new_connections",
    Localizable("New Connections"),
    Unit.PER_SECOND,
    Color.LIGHT_PURPLE,
)

metric_aws_new_tls_connections = metric.Metric(
    "aws_new_tls_connections",
    Localizable("New TLS Connections"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_rejected_connections = metric.Metric(
    "aws_rejected_connections",
    Localizable("Rejected Connections"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_client_tls_errors = metric.Metric(
    "aws_client_tls_errors",
    Localizable("Client TLS errors"),
    Unit.PER_SECOND,
    Color.YELLOW,
)

metric_aws_http_redirects = metric.Metric(
    "aws_http_redirects",
    Localizable("HTTP Redirects"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_http_redirect_url_limit = metric.Metric(
    "aws_http_redirect_url_limit",
    Localizable("HTTP Redirects URL Limit Exceeded"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_http_fixed_response = metric.Metric(
    "aws_http_fixed_response",
    Localizable("HTTP Fixed Responses"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_proc_bytes = metric.Metric(
    "aws_proc_bytes",
    Localizable("Processed Bytes"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.PURPLE,
)

metric_aws_proc_bytes_tls = metric.Metric(
    "aws_proc_bytes_tls",
    Localizable("TLS Processed Bytes"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.PURPLE,
)

metric_aws_ipv6_proc_bytes = metric.Metric(
    "aws_ipv6_proc_bytes",
    Localizable("IPv6 Processed Bytes"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.LIGHT_PURPLE,
)

metric_aws_ipv6_requests = metric.Metric(
    "aws_ipv6_requests",
    Localizable("IPv6 Requests"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_rule_evaluations = metric.Metric(
    "aws_rule_evaluations",
    Localizable("Rule Evaluations"),
    Unit.PER_SECOND,
    Color.YELLOW,
)

metric_aws_failed_tls_client_handshake = metric.Metric(
    "aws_failed_tls_client_handshake",
    Localizable("Failed TLS Client Handshake"),
    Unit.PER_SECOND,
    Color.YELLOW,
)

metric_aws_failed_tls_target_handshake = metric.Metric(
    "aws_failed_tls_target_handshake",
    Localizable("Failed TLS Target Handshake"),
    Unit.PER_SECOND,
    Color.YELLOW,
)

metric_aws_tcp_client_rst = metric.Metric(
    "aws_tcp_client_rst",
    Localizable("TCP Client Resets"),
    Unit.PER_SECOND,
    Color.LIGHT_GREEN,
)

metric_aws_tcp_elb_rst = metric.Metric(
    "aws_tcp_elb_rst",
    Localizable("TCP ELB Resets"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_tcp_target_rst = metric.Metric(
    "aws_tcp_target_rst",
    Localizable("TCP Target Resets"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_s3_downloads = metric.Metric(
    "aws_s3_downloads",
    Localizable("Download"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.YELLOW,
)

metric_aws_s3_uploads = metric.Metric(
    "aws_s3_uploads",
    Localizable("Upload"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.LIGHT_GREEN,
)

metric_aws_s3_select_object_scanned = metric.Metric(
    "aws_s3_select_object_scanned",
    Localizable("SELECT Object Scanned"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.LIGHT_GREEN,
)

metric_aws_s3_select_object_returned = metric.Metric(
    "aws_s3_select_object_returned",
    Localizable("SELECT Object Returned"),
    Unit.BYTES_IEC_PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_s3_buckets = metric.Metric(
    "aws_s3_buckets",
    Localizable("Buckets"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_elb_load_balancers = metric.Metric(
    "aws_elb_load_balancers",
    Localizable("Load balancers"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_elb_load_balancer_listeners = metric.Metric(
    "aws_elb_load_balancer_listeners",
    Localizable("Load balancer listeners"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_elb_load_balancer_registered_instances = metric.Metric(
    "aws_elb_load_balancer_registered_instances",
    Localizable("Load balancer registered instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_rds_db_clusters = metric.Metric(
    "aws_rds_db_clusters",
    Localizable("DB clusters"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_rds_db_cluster_parameter_groups = metric.Metric(
    "aws_rds_db_cluster_parameter_groups",
    Localizable("DB cluster parameter groups"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_rds_db_instances = metric.Metric(
    "aws_rds_db_instances",
    Localizable("DB instances"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_rds_event_subscriptions = metric.Metric(
    "aws_rds_event_subscriptions",
    Localizable("Event subscriptions"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_rds_manual_snapshots = metric.Metric(
    "aws_rds_manual_snapshots",
    Localizable("Manual snapshots"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_rds_option_groups = metric.Metric(
    "aws_rds_option_groups",
    Localizable("Option groups"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_rds_db_parameter_groups = metric.Metric(
    "aws_rds_db_parameter_groups",
    Localizable("DB parameter groups"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_rds_read_replica_per_master = metric.Metric(
    "aws_rds_read_replica_per_master",
    Localizable("Read replica per master"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_rds_reserved_db_instances = metric.Metric(
    "aws_rds_reserved_db_instances",
    Localizable("Reserved DB instances"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_rds_db_security_groups = metric.Metric(
    "aws_rds_db_security_groups",
    Localizable("DB security groups"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_rds_db_subnet_groups = metric.Metric(
    "aws_rds_db_subnet_groups",
    Localizable("DB subnet groups"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_rds_subnet_per_db_subnet_groups = metric.Metric(
    "aws_rds_subnet_per_db_subnet_groups",
    Localizable("Subnet per DB subnet groups"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_rds_allocated_storage = metric.Metric(
    "aws_rds_allocated_storage",
    Localizable("Allocated storage"),
    Unit.BYTES_IEC,
    Color.LIGHT_GREEN,
)

metric_aws_rds_auths_per_db_security_groups = metric.Metric(
    "aws_rds_auths_per_db_security_groups",
    Localizable("Authorizations per DB security group"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_rds_db_cluster_roles = metric.Metric(
    "aws_rds_db_cluster_roles",
    Localizable("DB cluster roles"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_ebs_block_store_snapshots = metric.Metric(
    "aws_ebs_block_store_snapshots",
    Localizable("Block store snapshots"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_ebs_block_store_space_standard = metric.Metric(
    "aws_ebs_block_store_space_standard",
    Localizable("Magnetic volumes space"),
    Unit.BYTES_IEC,
    Color.PURPLE,
)

metric_aws_ebs_block_store_space_io1 = metric.Metric(
    "aws_ebs_block_store_space_io1",
    Localizable("Provisioned IOPS SSD (io1) space"),
    Unit.BYTES_IEC,
    Color.LIGHT_PURPLE,
)

metric_aws_ebs_block_store_iops_io1 = metric.Metric(
    "aws_ebs_block_store_iops_io1",
    Localizable("Provisioned IOPS SSD (io1) IO operations per second"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_ebs_block_store_space_io2 = metric.Metric(
    "aws_ebs_block_store_space_io2",
    Localizable("Provisioned IOPS SSD (io2) space"),
    Unit.BYTES_IEC,
    Color.YELLOW,
)

metric_aws_ebs_block_store_iops_io2 = metric.Metric(
    "aws_ebs_block_store_iops_io2",
    Localizable("Provisioned IOPS SSD (io2) IO operations per second"),
    Unit.PER_SECOND,
    Color.YELLOW,
)

metric_aws_ebs_block_store_space_gp2 = metric.Metric(
    "aws_ebs_block_store_space_gp2",
    Localizable("General Purpose SSD (gp2) space"),
    Unit.BYTES_IEC,
    Color.ORANGE,
)

metric_aws_ebs_block_store_space_gp3 = metric.Metric(
    "aws_ebs_block_store_space_gp3",
    Localizable("General Purpose SSD (gp3) space"),
    Unit.BYTES_IEC,
    Color.YELLOW,
)

metric_aws_ebs_block_store_space_sc1 = metric.Metric(
    "aws_ebs_block_store_space_sc1",
    Localizable("Cold HDD space"),
    Unit.BYTES_IEC,
    Color.ORANGE,
)

metric_aws_ebs_block_store_space_st1 = metric.Metric(
    "aws_ebs_block_store_space_st1",
    Localizable("Throughput Optimized HDD space"),
    Unit.BYTES_IEC,
    Color.YELLOW,
)

metric_aws_elbv2_application_load_balancers = metric.Metric(
    "aws_elbv2_application_load_balancers",
    Localizable("Application Load balancers"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_elbv2_application_load_balancer_rules = metric.Metric(
    "aws_elbv2_application_load_balancer_rules",
    Localizable("Application Load Balancer Rules"),
    Unit.COUNT,
    Color.LIGHT_PURPLE,
)

metric_aws_elbv2_application_load_balancer_listeners = metric.Metric(
    "aws_elbv2_application_load_balancer_listeners",
    Localizable("Application Load Balancer Listeners"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_elbv2_application_load_balancer_target_groups = metric.Metric(
    "aws_elbv2_application_load_balancer_target_groups",
    Localizable("Application Load Balancer Target Groups"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_elbv2_application_load_balancer_certificates = metric.Metric(
    "aws_elbv2_application_load_balancer_certificates",
    Localizable("Application Load balancer Certificates"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_elbv2_network_load_balancers = metric.Metric(
    "aws_elbv2_network_load_balancers",
    Localizable("Network Load balancers"),
    Unit.COUNT,
    Color.DARK_YELLOW,
)

metric_aws_elbv2_network_load_balancer_listeners = metric.Metric(
    "aws_elbv2_network_load_balancer_listeners",
    Localizable("Network Load Balancer Listeners"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_elbv2_network_load_balancer_target_groups = metric.Metric(
    "aws_elbv2_network_load_balancer_target_groups",
    Localizable("Network Load Balancer Target Groups"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_elbv2_load_balancer_target_groups = metric.Metric(
    "aws_elbv2_load_balancer_target_groups",
    Localizable("Load balancers Target Groups"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_number_of_tables = metric.Metric(
    "aws_dynamodb_number_of_tables",
    Localizable("Number of tables"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_dynamodb_read_capacity = metric.Metric(
    "aws_dynamodb_read_capacity",
    Localizable("Read Capacity"),
    Unit.READ_CAPACITY_UNIT,
    Color.ORANGE,
)

metric_aws_dynamodb_write_capacity = metric.Metric(
    "aws_dynamodb_write_capacity",
    Localizable("Write Capacity"),
    Unit.WRITE_CAPACITY_UNIT,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_rcu = metric.Metric(
    "aws_dynamodb_consumed_rcu",
    Localizable("Average consumption"),
    Unit.READ_CAPACITY_UNIT,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_rcu_perc = metric.Metric(
    "aws_dynamodb_consumed_rcu_perc",
    Localizable("Average usage"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_wcu = metric.Metric(
    "aws_dynamodb_consumed_wcu",
    Localizable("Average consumption"),
    Unit.WRITE_CAPACITY_UNIT,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_consumed_wcu_perc = metric.Metric(
    "aws_dynamodb_consumed_wcu_perc",
    Localizable("Average usage"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_minimum_consumed_rcu = metric.Metric(
    "aws_dynamodb_minimum_consumed_rcu",
    Localizable("Minimum single-request consumption"),
    Unit.READ_CAPACITY_UNIT,
    Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_rcu = metric.Metric(
    "aws_dynamodb_maximum_consumed_rcu",
    Localizable("Maximum single-request consumption"),
    Unit.READ_CAPACITY_UNIT,
    Color.ORANGE,
)

metric_aws_dynamodb_minimum_consumed_wcu = metric.Metric(
    "aws_dynamodb_minimum_consumed_wcu",
    Localizable("Minimum single-request consumption"),
    Unit.WRITE_CAPACITY_UNIT,
    Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_wcu = metric.Metric(
    "aws_dynamodb_maximum_consumed_wcu",
    Localizable("Maximum single-request consumption"),
    Unit.WRITE_CAPACITY_UNIT,
    Color.ORANGE,
)

metric_aws_dynamodb_query_average_latency = metric.Metric(
    "aws_dynamodb_query_average_latency",
    Localizable("Average latency of successful Query requests"),
    Unit.SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_query_maximum_latency = metric.Metric(
    "aws_dynamodb_query_maximum_latency",
    Localizable("Maximum latency of successful Query requests"),
    Unit.SECOND,
    Color.ORANGE,
)

metric_aws_dynamodb_getitem_average_latency = metric.Metric(
    "aws_dynamodb_getitem_average_latency",
    Localizable("Average latency of successful GetItem requests"),
    Unit.SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_getitem_maximum_latency = metric.Metric(
    "aws_dynamodb_getitem_maximum_latency",
    Localizable("Maximum latency of successful GetItem requests"),
    Unit.SECOND,
    Color.ORANGE,
)

metric_aws_dynamodb_putitem_average_latency = metric.Metric(
    "aws_dynamodb_putitem_average_latency",
    Localizable("Average latency of successful PutItem requests"),
    Unit.SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_dynamodb_putitem_maximum_latency = metric.Metric(
    "aws_dynamodb_putitem_maximum_latency",
    Localizable("Maximum latency of successful PutItem requests"),
    Unit.SECOND,
    Color.ORANGE,
)

metric_aws_wafv2_web_acls = metric.Metric(
    "aws_wafv2_web_acls",
    Localizable("Number of Web ACLs"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_wafv2_rule_groups = metric.Metric(
    "aws_wafv2_rule_groups",
    Localizable("Number of rule groups"),
    Unit.COUNT,
    Color.ORANGE,
)

metric_aws_wafv2_ip_sets = metric.Metric(
    "aws_wafv2_ip_sets",
    Localizable("Number of IP sets"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_wafv2_regex_pattern_sets = metric.Metric(
    "aws_wafv2_regex_pattern_sets",
    Localizable("Number of regex sets"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_wafv2_web_acl_capacity_units = metric.Metric(
    "aws_wafv2_web_acl_capacity_units",
    Localizable("Web ACL capacity units (WCUs)"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_wafv2_requests_rate = metric.Metric(
    "aws_wafv2_requests_rate",
    Localizable("Avg. request rate"),
    Unit.PER_SECOND,
    Color.DARK_BROWN,
)

metric_aws_wafv2_allowed_requests_rate = metric.Metric(
    "aws_wafv2_allowed_requests_rate",
    Localizable("Avg. rate of allowed requests"),
    Unit.PER_SECOND,
    Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_rate = metric.Metric(
    "aws_wafv2_blocked_requests_rate",
    Localizable("Avg. rate of blocked requests"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_wafv2_allowed_requests_perc = metric.Metric(
    "aws_wafv2_allowed_requests_perc",
    Localizable("Percentage of allowed requests"),
    Unit.PERCENTAGE,
    Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_perc = metric.Metric(
    "aws_wafv2_blocked_requests_perc",
    Localizable("Percentage of blocked requests"),
    Unit.PERCENTAGE,
    Color.ORANGE,
)

metric_aws_cloudwatch_alarms_cloudwatch_alarms = metric.Metric(
    "aws_cloudwatch_alarms_cloudwatch_alarms",
    Localizable("CloudWatch alarms"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_duration = metric.Metric(
    "aws_lambda_duration",
    Localizable("Duration of Lambda functions"),
    Unit.SECOND,
    Color.PURPLE,
)

metric_aws_lambda_duration_in_percent = metric.Metric(
    "aws_lambda_duration_in_percent",
    Localizable("Duration in percent of Lambda timeout"),
    Unit.PERCENTAGE,
    Color.ORANGE,
)

metric_aws_lambda_invocations = metric.Metric(
    "aws_lambda_invocations",
    Localizable("Invocations"),
    Unit.PER_SECOND,
    Color.ORANGE,
)

metric_aws_lambda_throttles = metric.Metric(
    "aws_lambda_throttles",
    Localizable("Throttles"),
    Unit.PER_SECOND,
    Color.DARK_YELLOW,
)

metric_aws_lambda_iterator_age = metric.Metric(
    "aws_lambda_iterator_age",
    Localizable("Iterator age"),
    Unit.SECOND,
    Color.LIGHT_GREEN,
)

metric_aws_lambda_dead_letter_errors = metric.Metric(
    "aws_lambda_dead_letter_errors",
    Localizable("Dead letter errors"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_init_duration_absolute = metric.Metric(
    "aws_lambda_init_duration_absolute",
    Localizable("Init duration"),
    Unit.SECOND,
    Color.BLUE,
)

metric_aws_lambda_cold_starts_in_percent = metric.Metric(
    "aws_lambda_cold_starts_in_percent",
    Localizable("Cold starts in percent"),
    Unit.PERCENTAGE,
    Color.PURPLE,
)

metric_aws_lambda_concurrent_executions_in_percent = metric.Metric(
    "aws_lambda_concurrent_executions_in_percent",
    Localizable("Concurrent executions in percent"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_concurrent_executions = metric.Metric(
    "aws_lambda_concurrent_executions",
    Localizable("Concurrent executions"),
    Unit.PER_SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_unreserved_concurrent_executions_in_percent = metric.Metric(
    "aws_lambda_unreserved_concurrent_executions_in_percent",
    Localizable("Unreserved concurrent executions in percent"),
    Unit.PERCENTAGE,
    Color.DARK_YELLOW,
)

metric_aws_lambda_unreserved_concurrent_executions = metric.Metric(
    "aws_lambda_unreserved_concurrent_executions",
    Localizable("Unreserved concurrent executions"),
    Unit.PER_SECOND,
    Color.DARK_YELLOW,
)

metric_aws_lambda_provisioned_concurrency_executions = metric.Metric(
    "aws_lambda_provisioned_concurrency_executions",
    Localizable("Provisioned concurrency executions"),
    Unit.PER_SECOND,
    Color.BLUE,
)

metric_aws_lambda_provisioned_concurrency_invocations = metric.Metric(
    "aws_lambda_provisioned_concurrency_invocations",
    Localizable("Provisioned concurrency invocations"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_lambda_provisioned_concurrency_spillover_invocations = metric.Metric(
    "aws_lambda_provisioned_concurrency_spillover_invocations",
    Localizable("Provisioned concurrency spillover invocations"),
    Unit.PER_SECOND,
    Color.PURPLE,
)

metric_aws_lambda_provisioned_concurrency_utilization = metric.Metric(
    "aws_lambda_provisioned_concurrency_utilization",
    Localizable("Provisioned concurrency utilization"),
    Unit.PERCENTAGE,
    Color.LIGHT_GREEN,
)

metric_aws_lambda_code_size_in_percent = metric.Metric(
    "aws_lambda_code_size_in_percent",
    Localizable("Code Size in percent"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_code_size_absolute = metric.Metric(
    "aws_lambda_code_size_absolute",
    Localizable("Code Size"),
    Unit.BYTES_IEC,
    Color.LIGHT_BLUE,
)

metric_aws_lambda_memory_size_in_percent = metric.Metric(
    "aws_lambda_memory_size_in_percent",
    Localizable("Memory Size in percent"),
    Unit.PERCENTAGE,
    Color.BLUE,
)

metric_aws_lambda_memory_size_absolute = metric.Metric(
    "aws_lambda_memory_size_absolute",
    Localizable("Memory Size"),
    Unit.BYTES_IEC,
    Color.PURPLE,
)

metric_aws_route53_child_health_check_healthy_count = metric.Metric(
    "aws_route53_child_health_check_healthy_count",
    Localizable("Health check healty count"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_route53_connection_time = metric.Metric(
    "aws_route53_connection_time",
    Localizable("Connection time"),
    Unit.SECOND,
    Color.LIGHT_BLUE,
)

metric_aws_route53_health_check_percentage_healthy = metric.Metric(
    "aws_route53_health_check_percentage_healthy",
    Localizable("Health check percentage healty"),
    Unit.PERCENTAGE,
    Color.PURPLE,
)

metric_aws_route53_ssl_handshake_time = metric.Metric(
    "aws_route53_ssl_handshake_time",
    Localizable("SSL handshake time"),
    Unit.SECOND,
    Color.PURPLE,
)

metric_aws_route53_time_to_first_byte = metric.Metric(
    "aws_route53_time_to_first_byte",
    Localizable("Time to first byte"),
    Unit.SECOND,
    Color.PURPLE,
)

metric_aws_sns_topics_standard = metric.Metric(
    "aws_sns_topics_standard",
    Localizable("Standard Topics"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_sns_topics_fifo = metric.Metric(
    "aws_sns_topics_fifo",
    Localizable("FIFO Topics"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_cloudfront_requests = metric.Metric(
    "aws_cloudfront_requests",
    Localizable("Requests"),
    Unit.COUNT,
    Color.PURPLE,
)

metric_aws_cloudfront_total_error_rate = metric.Metric(
    "aws_cloudfront_total_error_rate",
    Localizable("Total error rate"),
    Unit.PERCENTAGE,
    Color.YELLOW,
)

metric_aws_cloudfront_4xx_error_rate = metric.Metric(
    "aws_cloudfront_4xx_error_rate",
    Localizable("4xx error rate"),
    Unit.PERCENTAGE,
    Color.LIGHT_GREEN,
)

metric_aws_cloudfront_5xx_error_rate = metric.Metric(
    "aws_cloudfront_5xx_error_rate",
    Localizable("5xx error rate"),
    Unit.PERCENTAGE,
    Color.LIGHT_BLUE,
)

metric_aws_ecs_clusters = metric.Metric(
    "aws_ecs_clusters",
    Localizable("Clusters"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_aws_elasticache_nodes = metric.Metric(
    "aws_elasticache_nodes",
    Localizable("Nodes"),
    Unit.COUNT,
    Color.YELLOW,
)

metric_aws_elasticache_parameter_groups = metric.Metric(
    "aws_elasticache_parameter_groups",
    Localizable("Parameter groups"),
    Unit.COUNT,
    Color.LIGHT_GREEN,
)

metric_aws_elasticache_subnet_groups = metric.Metric(
    "aws_elasticache_subnet_groups",
    Localizable("Subnet groups"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)
