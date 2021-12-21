#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.aws_constants import AWSEC2InstFamilies, AWSEC2InstTypes

from cmk.gui.i18n import _l
from cmk.gui.plugins.metrics.utils import graph_info, indexed_color, metric_info

# .
#   .--Metrics-------------------------------------------------------------.
#   |                   __  __      _        _                             |
#   |                  |  \/  | ___| |_ _ __(_) ___ ___                    |
#   |                  | |\/| |/ _ \ __| '__| |/ __/ __|                   |
#   |                  | |  | |  __/ |_| |  | | (__\__ \                   |
#   |                  |_|  |_|\___|\__|_|  |_|\___|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definitions of metrics                                              |
#   '----------------------------------------------------------------------'

# Title are always lower case - except the first character!
# Colors: See indexed_color() in cmk/gui/plugins/metrics/utils.py

metric_info["aws_costs_unblended"] = {
    "title": _l("Unblended costs"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_glacier_number_of_vaults"] = {
    "title": _l("Number of vaults"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_glacier_num_archives"] = {
    "title": _l("Number of archives"),
    "unit": "count",
    "color": "21/a",
}

metric_info["aws_glacier_vault_size"] = {
    "title": _l("Vault size"),
    "unit": "bytes",
    "color": "15/a",
}

metric_info["aws_glacier_total_vault_size"] = {
    "title": _l("Total size of all vaults"),
    "unit": "bytes",
    "color": "15/a",
}

metric_info["aws_glacier_largest_vault_size"] = {
    "title": _l("Largest vault size"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["aws_num_objects"] = {
    "title": _l("Number of objects"),
    "unit": "count",
    "color": "21/a",
}

metric_info["aws_bucket_size"] = {
    "title": _l("Bucket size"),
    "unit": "bytes",
    "color": "15/a",
}

metric_info["aws_largest_bucket_size"] = {
    "title": _l("Largest bucket size"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["aws_surge_queue_length"] = {
    "title": _l("Surge queue length"),
    "unit": "count",
    "color": "12/a",
}

metric_info["aws_spillover"] = {
    "title": _l("The rate of requests that were rejected (spillover)"),
    "unit": "1/s",
    "color": "13/a",
}

metric_info["aws_load_balancer_latency"] = {
    "title": _l("Load balancer latency"),
    "unit": "s",
    "color": "21/a",
}


def register_aws_http_metrics():
    for http_err_code, color in zip(
        ["2xx", "3xx", "4xx", "5xx", "500", "502", "503", "504"],
        ["53/a", "11/a", "32/a", "42/a", "13/a", "14/a", "16/b", "34/a"],
    ):
        metric_info["aws_http_%s_rate" % http_err_code] = {
            "title": _l("HTTP %s errors") % http_err_code.upper(),
            "unit": "1/s",
            "color": color,
        }
        metric_info["aws_http_%s_perc" % http_err_code] = {
            "title": _l("Percentage of HTTP %s errors") % http_err_code.upper(),
            "unit": "%",
            "color": color,
        }


register_aws_http_metrics()

metric_info["aws_lambda_users_errors_rate"] = {
    "title": _l("Lambda user errors"),
    "unit": "1/s",
    "color": "42/a",
}
metric_info["aws_lambda_users_errors_perc"] = {
    "title": _l("Percentage of Lambda user errors"),
    "unit": "%",
    "color": "42/a",
}

metric_info["aws_overall_hosts_health_perc"] = {
    "title": _l("Proportion of healthy host"),
    "unit": "%",
    "color": "35/a",
}

metric_info["aws_backend_connection_errors_rate"] = {
    "title": _l("Backend connection errors"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["aws_burst_balance"] = {
    "title": _l("Burst Balance"),
    "unit": "%",
    "color": "11/a",
}

metric_info["aws_cpu_credit_balance"] = {
    "title": _l("CPU Credit Balance"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_rds_bin_log_disk_usage"] = {
    "title": _l("Bin Log Disk Usage"),
    "unit": "%",
    "color": "11/a",
}

metric_info["aws_rds_transaction_logs_disk_usage"] = {
    "title": _l("Transaction Logs Disk Usage"),
    "unit": "%",
    "color": "12/a",
}

metric_info["aws_rds_replication_slot_disk_usage"] = {
    "title": _l("Replication Slot Disk Usage"),
    "unit": "%",
    "color": "13/a",
}

metric_info["aws_rds_replica_lag"] = {
    "title": _l("Replica Lag"),
    "unit": "s",
    "color": "14/a",
}

metric_info["aws_rds_oldest_replication_slot_lag"] = {
    "title": _l("Oldest Replication Slot Lag Size"),
    "unit": "bytes",
    "color": "14/a",
}

metric_info["aws_rds_connections"] = {
    "title": _l("Connections in use"),
    "unit": "count",
    "color": "21/a",
}

metric_info["aws_request_latency"] = {
    "title": _l("Request latency"),
    "unit": "s",
    "color": "21/a",
}

metric_info["aws_ec2_vpc_elastic_ip_addresses"] = {
    "title": _l("VPC Elastic IP Addresses"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_ec2_elastic_ip_addresses"] = {
    "title": _l("Elastic IP Addresses"),
    "unit": "count",
    "color": "13/a",
}

metric_info["aws_ec2_spot_inst_requests"] = {
    "title": _l("Spot Instance Requests"),
    "unit": "count",
    "color": "15/a",
}

metric_info["aws_ec2_active_spot_fleet_requests"] = {
    "title": _l("Active Spot Fleet Requests"),
    "unit": "count",
    "color": "21/a",
}

metric_info["aws_ec2_spot_fleet_total_target_capacity"] = {
    "title": _l("Spot Fleet Requests Total Target Capacity"),
    "unit": "count",
    "color": "23/a",
}

metric_info["aws_ec2_running_ondemand_instances_total"] = {
    "title": _l("Total running On-Demand Instances"),
    "unit": "count",
    "color": "#000000",
}

for i, inst_type in enumerate(AWSEC2InstTypes):
    metric_info["aws_ec2_running_ondemand_instances_%s" % inst_type] = {
        "title": _l("Total running On-Demand %s Instances") % inst_type,
        "unit": "count",
        "color": indexed_color(i, len(AWSEC2InstTypes)),
    }

for inst_fam, inst_fam_title in AWSEC2InstFamilies.items():
    metric_info["aws_ec2_running_ondemand_instances_%s_vcpu" % inst_fam[0]] = {
        "title": _l("Total %s vCPUs") % inst_fam_title,
        "unit": "count",
        "color": "25/a",
    }

metric_info["aws_consumed_lcus"] = {
    "title": _l("Consumed Load Balancer Capacity Units"),
    "unit": "",
    "color": "11/a",
}

metric_info["aws_active_connections"] = {
    "title": _l("Active Connections"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["aws_active_tls_connections"] = {
    "title": _l("Active TLS Connections"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["aws_new_connections"] = {
    "title": _l("New Connections"),
    "unit": "1/s",
    "color": "13/a",
}

metric_info["aws_new_tls_connections"] = {
    "title": _l("New TLS Connections"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["aws_rejected_connections"] = {
    "title": _l("Rejected Connections"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["aws_client_tls_errors"] = {
    "title": _l("Client TLS errors"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["aws_http_redirects"] = {
    "title": _l("HTTP Redirects"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["aws_http_redirect_url_limit"] = {
    "title": _l("HTTP Redirects URL Limit Exceeded"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["aws_http_fixed_response"] = {
    "title": _l("HTTP Fixed Responses"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["aws_proc_bytes"] = {
    "title": _l("Processed Bytes"),
    "unit": "bytes/s",
    "color": "11/a",
}

metric_info["aws_proc_bytes_tls"] = {
    "title": _l("TLS Processed Bytes"),
    "unit": "bytes/s",
    "color": "12/a",
}

metric_info["aws_ipv6_proc_bytes"] = {
    "title": _l("IPv6 Processed Bytes"),
    "unit": "bytes/s",
    "color": "13/a",
}

metric_info["aws_ipv6_requests"] = {
    "title": _l("IPv6 Requests"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["aws_rule_evaluations"] = {
    "title": _l("Rule Evaluations"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["aws_failed_tls_client_handshake"] = {
    "title": _l("Failed TLS Client Handshake"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["aws_failed_tls_target_handshake"] = {
    "title": _l("Failed TLS Target Handshake"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["aws_tcp_client_rst"] = {
    "title": _l("TCP Client Resets"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["aws_tcp_elb_rst"] = {
    "title": _l("TCP ELB Resets"),
    "unit": "1/s",
    "color": "33/a",
}

metric_info["aws_tcp_target_rst"] = {
    "title": _l("TCP Target Resets"),
    "unit": "1/s",
    "color": "35/a",
}

metric_info["aws_s3_downloads"] = {
    "title": _l("Download"),
    "unit": "bytes/s",
    "color": "21/a",
}

metric_info["aws_s3_uploads"] = {
    "title": _l("Upload"),
    "unit": "bytes/s",
    "color": "31/a",
}

metric_info["aws_s3_select_object_scanned"] = {
    "title": _l("SELECT Object Scanned"),
    "unit": "bytes/s",
    "color": "31/a",
}

metric_info["aws_s3_select_object_returned"] = {
    "title": _l("SELECT Object Returned"),
    "unit": "bytes/s",
    "color": "41/a",
}

metric_info["aws_s3_buckets"] = {
    "title": _l("Buckets"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_elb_load_balancers"] = {
    "title": _l("Load balancers"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_elb_load_balancer_listeners"] = {
    "title": _l("Load balancer listeners"),
    "unit": "count",
    "color": "12/a",
}

metric_info["aws_elb_load_balancer_registered_instances"] = {
    "title": _l("Load balancer registered instances"),
    "unit": "count",
    "color": "13/a",
}

metric_info["aws_rds_db_clusters"] = {
    "title": _l("DB clusters"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_rds_db_cluster_parameter_groups"] = {
    "title": _l("DB cluster parameter groups"),
    "unit": "count",
    "color": "12/a",
}

metric_info["aws_rds_db_instances"] = {
    "title": _l("DB instances"),
    "unit": "count",
    "color": "13/a",
}

metric_info["aws_rds_event_subscriptions"] = {
    "title": _l("Event subscriptions"),
    "unit": "count",
    "color": "14/a",
}

metric_info["aws_rds_manual_snapshots"] = {
    "title": _l("Manual snapshots"),
    "unit": "count",
    "color": "15/a",
}

metric_info["aws_rds_option_groups"] = {
    "title": _l("Option groups"),
    "unit": "count",
    "color": "16/a",
}

metric_info["aws_rds_db_parameter_groups"] = {
    "title": _l("DB parameter groups"),
    "unit": "count",
    "color": "21/a",
}

metric_info["aws_rds_read_replica_per_master"] = {
    "title": _l("Read replica per master"),
    "unit": "count",
    "color": "22/a",
}

metric_info["aws_rds_reserved_db_instances"] = {
    "title": _l("Reserved DB instances"),
    "unit": "count",
    "color": "23/a",
}

metric_info["aws_rds_db_security_groups"] = {
    "title": _l("DB security groups"),
    "unit": "count",
    "color": "24/a",
}

metric_info["aws_rds_db_subnet_groups"] = {
    "title": _l("DB subnet groups"),
    "unit": "count",
    "color": "25/a",
}

metric_info["aws_rds_subnet_per_db_subnet_groups"] = {
    "title": _l("Subnet per DB subnet groups"),
    "unit": "count",
    "color": "26/a",
}

metric_info["aws_rds_allocated_storage"] = {
    "title": _l("Allocated storage"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["aws_rds_auths_per_db_security_groups"] = {
    "title": _l("Authorizations per DB security group"),
    "unit": "count",
    "color": "32/a",
}

metric_info["aws_rds_db_cluster_roles"] = {
    "title": _l("DB cluster roles"),
    "unit": "count",
    "color": "33/a",
}

metric_info["aws_ebs_block_store_snapshots"] = {
    "title": _l("Block store snapshots"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_ebs_block_store_space_standard"] = {
    "title": _l("Magnetic volumes space"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["aws_ebs_block_store_space_io1"] = {
    "title": _l("Provisioned IOPS SSD space"),
    "unit": "bytes",
    "color": "13/a",
}

metric_info["aws_ebs_block_store_iops_io1"] = {
    "title": _l("Provisioned IOPS SSD IO operations per second"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["aws_ebs_block_store_space_gp2"] = {
    "title": _l("General Purpose SSD space"),
    "unit": "bytes",
    "color": "15/a",
}

metric_info["aws_ebs_block_store_space_sc1"] = {
    "title": _l("Cold HDD space"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["aws_ebs_block_store_space_st1"] = {
    "title": _l("Throughput Optimized HDD space"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["aws_elbv2_application_load_balancers"] = {
    "title": _l("Application Load balancers"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_elbv2_application_load_balancer_rules"] = {
    "title": _l("Application Load Balancer Rules"),
    "unit": "count",
    "color": "13/a",
}

metric_info["aws_elbv2_application_load_balancer_listeners"] = {
    "title": _l("Application Load Balancer Listeners"),
    "unit": "count",
    "color": "15/a",
}

metric_info["aws_elbv2_application_load_balancer_target_groups"] = {
    "title": _l("Application Load Balancer Target Groups"),
    "unit": "count",
    "color": "21/a",
}

metric_info["aws_elbv2_application_load_balancer_certificates"] = {
    "title": _l("Application Load balancer Certificates"),
    "unit": "count",
    "color": "23/a",
}

metric_info["aws_elbv2_network_load_balancers"] = {
    "title": _l("Network Load balancers"),
    "unit": "count",
    "color": "25/a",
}

metric_info["aws_elbv2_network_load_balancer_listeners"] = {
    "title": _l("Network Load Balancer Listeners"),
    "unit": "count",
    "color": "31/a",
}

metric_info["aws_elbv2_network_load_balancer_target_groups"] = {
    "title": _l("Network Load Balancer Target Groups"),
    "unit": "count",
    "color": "33/a",
}

metric_info["aws_elbv2_load_balancer_target_groups"] = {
    "title": _l("Load balancers Target Groups"),
    "unit": "count",
    "color": "35/a",
}

metric_info["aws_dynamodb_number_of_tables"] = {
    "title": _l("Number of tables"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_dynamodb_read_capacity"] = {
    "title": _l("Read Capacity"),
    "unit": "RCU",
    "color": "16/a",
}

metric_info["aws_dynamodb_write_capacity"] = {
    "title": _l("Write Capacity"),
    "unit": "WCU",
    "color": "41/a",
}

metric_info["aws_dynamodb_consumed_rcu"] = {
    "title": _l("Average consumption"),
    "unit": "RCU",
    "color": "41/a",
}

metric_info["aws_dynamodb_consumed_rcu_perc"] = {
    "title": _l("Average usage"),
    "unit": "%",
    "color": "41/a",
}

metric_info["aws_dynamodb_consumed_wcu"] = {
    "title": _l("Average consumption"),
    "unit": "RCU",
    "color": "41/a",
}

metric_info["aws_dynamodb_consumed_wcu_perc"] = {
    "title": _l("Average usage"),
    "unit": "%",
    "color": "41/a",
}

metric_info["aws_dynamodb_minimum_consumed_rcu"] = {
    "title": _l("Minimum single-request consumption"),
    "unit": "RCU",
    "color": "31/b",
}

metric_info["aws_dynamodb_maximum_consumed_rcu"] = {
    "title": _l("Maximum single-request consumption"),
    "unit": "RCU",
    "color": "15/a",
}

metric_info["aws_dynamodb_minimum_consumed_wcu"] = {
    "title": _l("Minimum single-request consumption"),
    "unit": "RCU",
    "color": "31/b",
}

metric_info["aws_dynamodb_maximum_consumed_wcu"] = {
    "title": _l("Maximum single-request consumption"),
    "unit": "RCU",
    "color": "15/a",
}

metric_info["aws_dynamodb_query_average_latency"] = {
    "title": _l("Average latency of successful Query requests"),
    "unit": "s",
    "color": "41/a",
}

metric_info["aws_dynamodb_query_maximum_latency"] = {
    "title": _l("Maximum latency of successful Query requests"),
    "unit": "s",
    "color": "15/a",
}

metric_info["aws_dynamodb_getitem_average_latency"] = {
    "title": _l("Average latency of successful GetItem requests"),
    "unit": "s",
    "color": "41/a",
}

metric_info["aws_dynamodb_getitem_maximum_latency"] = {
    "title": _l("Maximum latency of successful GetItem requests"),
    "unit": "s",
    "color": "15/a",
}

metric_info["aws_dynamodb_putitem_average_latency"] = {
    "title": _l("Average latency of successful PutItem requests"),
    "unit": "s",
    "color": "41/a",
}

metric_info["aws_dynamodb_putitem_maximum_latency"] = {
    "title": _l("Maximum latency of successful PutItem requests"),
    "unit": "s",
    "color": "15/a",
}

metric_info["aws_wafv2_web_acls"] = {
    "title": _l("Number of Web ACLs"),
    "unit": "count",
    "color": "41/a",
}

metric_info["aws_wafv2_rule_groups"] = {
    "title": _l("Number of rule groups"),
    "unit": "count",
    "color": "16/a",
}

metric_info["aws_wafv2_ip_sets"] = {
    "title": _l("Number of IP sets"),
    "unit": "count",
    "color": "31/b",
}

metric_info["aws_wafv2_regex_pattern_sets"] = {
    "title": _l("Number of regex sets"),
    "unit": "count",
    "color": "11/a",
}

metric_info["aws_wafv2_web_acl_capacity_units"] = {
    "title": _l("Web ACL capacity units (WCUs)"),
    "unit": "count",
    "color": "41/a",
}

metric_info["aws_wafv2_requests_rate"] = {
    "title": _l("Avg. request rate"),
    "unit": "1/s",
    "color": "#000000",
}

metric_info["aws_wafv2_allowed_requests_rate"] = {
    "title": _l("Avg. rate of allowed requests"),
    "unit": "1/s",
    "color": "26/b",
}

metric_info["aws_wafv2_blocked_requests_rate"] = {
    "title": _l("Avg. rate of blocked requests"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["aws_wafv2_allowed_requests_perc"] = {
    "title": _l("Percentage of allowed requests"),
    "unit": "%",
    "color": "26/b",
}

metric_info["aws_wafv2_blocked_requests_perc"] = {
    "title": _l("Percentage of blocked requests"),
    "unit": "%",
    "color": "16/a",
}

metric_info["aws_cloudwatch_alarms_cloudwatch_alarms"] = {
    "title": _l("CloudWatch alarms"),
    "unit": "count",
    "color": "41/a",
}

metric_info["aws_lambda_duration"] = {
    "title": _l("Duration of Lambda functions"),
    "unit": "s",
    "color": "12/a",
}

metric_info["aws_lambda_duration_in_percent"] = {
    "title": _l("Duration in percent of Lambda timeout"),
    "unit": "%",
    "color": "14/a",
}

metric_info["aws_lambda_invocations"] = {
    "title": _l("Invocations"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["aws_lambda_throttles"] = {
    "title": _l("Throttles"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["aws_lambda_iterator_age"] = {
    "title": _l("Iterator age"),
    "unit": "s",
    "color": "31/a",
}

metric_info["aws_lambda_dead_letter_errors"] = {
    "title": _l("Dead letter errors"),
    "unit": "1/s",
    "color": "41/a",
}

metric_info["aws_lambda_init_duration_absolute"] = {
    "title": _l("Init duration"),
    "unit": "s",
    "color": "43/a",
}

metric_info["aws_lambda_cold_starts_in_percent"] = {
    "title": _l("Cold starts in percent"),
    "unit": "%",
    "color": "44/a",
}

metric_info["aws_lambda_concurrent_executions_in_percent"] = {
    "title": _l("Concurrent executions in percent"),
    "unit": "%",
    "color": "35/a",
}

metric_info["aws_lambda_concurrent_executions"] = {
    "title": _l("Concurrent executions"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["aws_lambda_unreserved_concurrent_executions_in_percent"] = {
    "title": _l("Unreserved concurrent executions in percent"),
    "unit": "%",
    "color": "25/a",
}

metric_info["aws_lambda_unreserved_concurrent_executions"] = {
    "title": _l("Unreserved concurrent executions"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["aws_lambda_provisioned_concurrency_executions"] = {
    "title": _l("Provisioned concurrency executions"),
    "unit": "1/s",
    "color": "43/a",
}

metric_info["aws_lambda_provisioned_concurrency_invocations"] = {
    "title": _l("Provisioned concurrency invocations"),
    "unit": "1/s",
    "color": "44/a",
}

metric_info["aws_lambda_provisioned_concurrency_spillover_invocations"] = {
    "title": _l("Provisioned concurrency spillover invocations"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["aws_lambda_provisioned_concurrency_utilization"] = {
    "title": _l("Provisioned concurrency utilization"),
    "unit": "%",
    "color": "31/a",
}

metric_info["aws_lambda_code_size_in_percent"] = {
    "title": _l("Code Size in percent"),
    "unit": "%",
    "color": "41/a",
}

metric_info["aws_lambda_code_size_absolute"] = {
    "title": _l("Code Size"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["aws_lambda_memory_size_in_percent"] = {
    "title": _l("Memory Size in percent"),
    "unit": "%",
    "color": "43/a",
}

metric_info["aws_lambda_memory_size_absolute"] = {
    "title": _l("Memory Size"),
    "unit": "bytes",
    "color": "44/a",
}

metric_info["aws_route53_child_health_check_healthy_count"] = {
    "title": _l("Health check healty count"),
    "unit": "count",
    "color": "41/a",
}

metric_info["aws_route53_connection_time"] = {
    "title": _l("Connection time"),
    "unit": "s",
    "color": "42/a",
}

metric_info["aws_route53_health_check_percentage_healthy"] = {
    "title": _l("Health check percentage healty"),
    "unit": "%",
    "color": "44/a",
}

metric_info["aws_route53_ssl_handshake_time"] = {
    "title": _l("SSL handshake time"),
    "unit": "s",
    "color": "45/a",
}

metric_info["aws_route53_time_to_first_byte"] = {
    "title": _l("Time to first byte"),
    "unit": "s",
    "color": "46/a",
}


# .
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Definitions of time series graphs                                   |
#   '----------------------------------------------------------------------'

graph_info["aws_ec2_running_ondemand_instances"] = {
    "title": _l("Total running On-Demand Instances"),
    "metrics": [("aws_ec2_running_ondemand_instances_total", "line")]
    + [
        ("aws_ec2_running_ondemand_instances_%s" % inst_type, "stack")
        for inst_type in AWSEC2InstTypes
    ],
    "optional_metrics": [
        "aws_ec2_running_ondemand_instances_%s" % inst_type for inst_type in AWSEC2InstTypes
    ],
}

graph_info["aws_http_nxx_errors_rate"] = {
    "title": _l("HTTP 3/4/5XX Errors"),
    "metrics": [
        ("aws_http_2xx_rate", "stack"),
        ("aws_http_3xx_rate", "stack"),
        ("aws_http_4xx_rate", "stack"),
        ("aws_http_5xx_rate", "stack"),
    ],
    "optional_metrics": ["aws_http_2xx_rate", "aws_http_3xx_rate"],
}
graph_info["aws_http_50x_errors_rate"] = {
    "title": _l("HTTP 500/2/3/4 Errors"),
    "metrics": [
        ("aws_http_500_rate", "stack"),
        ("aws_http_502_rate", "stack"),
        ("aws_http_503_rate", "stack"),
        ("aws_http_504_rate", "stack"),
    ],
}
graph_info["aws_http_nxx_errors_perc"] = {
    "title": _l("Percentage of HTTP 3/4/5XX Errors"),
    "metrics": [
        ("aws_http_2xx_perc", "stack"),
        ("aws_http_3xx_perc", "stack"),
        ("aws_http_4xx_perc", "stack"),
        ("aws_http_5xx_perc", "stack"),
    ],
    "optional_metrics": ["aws_http_2xx_perc", "aws_http_3xx_perc"],
}
graph_info["aws_http_50x_errors_perc"] = {
    "title": _l("Percentage of HTTP 500/2/3/4 Errors"),
    "metrics": [
        ("aws_http_500_perc", "stack"),
        ("aws_http_502_perc", "stack"),
        ("aws_http_503_perc", "stack"),
        ("aws_http_504_perc", "stack"),
    ],
}

graph_info["aws_dynamodb_read_capacity_single"] = {
    "title": _l("Single-request consumption"),
    "metrics": [
        ("aws_dynamodb_minimum_consumed_rcu", "line"),
        ("aws_dynamodb_maximum_consumed_rcu", "line"),
    ],
}

graph_info["aws_dynamodb_write_capacity_single"] = {
    "title": _l("Single-request consumption"),
    "metrics": [
        ("aws_dynamodb_minimum_consumed_wcu", "line"),
        ("aws_dynamodb_maximum_consumed_wcu", "line"),
    ],
}

graph_info["aws_dynamodb_query_latency"] = {
    "title": _l("Latency of Query requests"),
    "metrics": [
        ("aws_dynamodb_query_average_latency", "line"),
        ("aws_dynamodb_query_maximum_latency", "line"),
    ],
}

graph_info["aws_dynamodb_getitem_latency"] = {
    "title": _l("Latency of GetItem requests"),
    "metrics": [
        ("aws_dynamodb_getitem_average_latency", "line"),
        ("aws_dynamodb_getitem_maximum_latency", "line"),
    ],
}

graph_info["aws_dynamodb_putitem_latency"] = {
    "title": _l("Latency of PutItem requests"),
    "metrics": [
        ("aws_dynamodb_putitem_average_latency", "line"),
        ("aws_dynamodb_putitem_maximum_latency", "line"),
    ],
}

graph_info["aws_wafv2_web_acl_requests"] = {
    "title": _l("Web ACL Requests"),
    "metrics": [
        ("aws_wafv2_allowed_requests_rate", "stack"),
        ("aws_wafv2_blocked_requests_rate", "stack"),
        ("aws_wafv2_requests_rate", "line"),
    ],
}
