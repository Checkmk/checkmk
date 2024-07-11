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
