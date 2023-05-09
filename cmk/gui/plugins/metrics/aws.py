#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    metric_info,
    graph_info,
    indexed_color,
)
from cmk.utils.aws_constants import AWSEC2InstTypes, AWSEC2InstFamilies

#.
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

metric_info['aws_costs_unblended'] = {
    'title': _('Unblended costs'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_glacier_number_of_vaults'] = {
    'title': _('Number of vaults'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_glacier_num_archives'] = {
    'title': _('Number of archives'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_glacier_vault_size'] = {
    'title': _('Vault size'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_glacier_total_vault_size'] = {
    'title': _('Total size of all vaults'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_glacier_largest_vault_size'] = {
    'title': _('Largest vault size'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_num_objects'] = {
    'title': _('Number of objects'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_bucket_size'] = {
    'title': _('Bucket size'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_largest_bucket_size'] = {
    'title': _('Largest bucket size'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_surge_queue_length'] = {
    'title': _('Surge queue length'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_spillover'] = {
    'title': _('The rate of requests that were rejected (spillover)'),
    'unit': '1/s',
    'color': '13/a',
}

metric_info["aws_load_balancer_latency"] = {
    "title": _("Load balancer latency"),
    "unit": "s",
    "color": "21/a",
}


def register_aws_http_metrics():
    for http_err_code, color in zip(
        ['2xx', '3xx', '4xx', '5xx', '500', '502', '503', '504'],
        ['53/a', '11/a', '32/a', '42/a', '13/a', '14/a', '16/b', '34/a']):
        metric_info["aws_http_%s_rate" % http_err_code] = {
            "title": _("HTTP %s errors" % http_err_code.upper()),
            "unit": "1/s",
            "color": color,
        }
        metric_info["aws_http_%s_perc" % http_err_code] = {
            "title": _("Percentage of HTTP %s errors" % http_err_code.upper()),
            "unit": "%",
            "color": color,
        }


register_aws_http_metrics()

metric_info["aws_lambda_users_errors_rate"] = {
    "title": _("Lambda user errors"),
    "unit": "1/s",
    "color": "42/a",
}
metric_info["aws_lambda_users_errors_perc"] = {
    "title": _("Percentage of Lambda user errors"),
    "unit": "%",
    "color": "42/a",
}

metric_info["aws_overall_hosts_health_perc"] = {
    "title": _("Proportion of healthy host"),
    "unit": "%",
    "color": "35/a",
}

metric_info['aws_backend_connection_errors_rate'] = {
    'title': _('Backend connection errors'),
    'unit': '1/s',
    'color': '15/a',
}

metric_info['aws_burst_balance'] = {
    'title': _('Burst Balance'),
    'unit': '%',
    'color': '11/a',
}

metric_info['aws_cpu_credit_balance'] = {
    'title': _('CPU Credit Balance'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_rds_bin_log_disk_usage'] = {
    'title': _('Bin Log Disk Usage'),
    'unit': '%',
    'color': '11/a',
}

metric_info['aws_rds_transaction_logs_disk_usage'] = {
    'title': _('Transaction Logs Disk Usage'),
    'unit': '%',
    'color': '12/a',
}

metric_info['aws_rds_replication_slot_disk_usage'] = {
    'title': _('Replication Slot Disk Usage'),
    'unit': '%',
    'color': '13/a',
}

metric_info['aws_rds_replica_lag'] = {
    'title': _('Replica Lag'),
    'unit': 's',
    'color': '14/a',
}

metric_info['aws_rds_oldest_replication_slot_lag'] = {
    'title': _('Oldest Replication Slot Lag Size'),
    'unit': 'bytes',
    'color': '14/a',
}

metric_info['aws_rds_connections'] = {
    'title': _('Connections in use'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_request_latency'] = {
    'title': _('Request latency'),
    'unit': 's',
    'color': '21/a',
}

metric_info['aws_ec2_vpc_elastic_ip_addresses'] = {
    'title': _('VPC Elastic IP Addresses'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_ec2_elastic_ip_addresses'] = {
    'title': _('Elastic IP Addresses'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_ec2_spot_inst_requests'] = {
    'title': _('Spot Instance Requests'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_ec2_active_spot_fleet_requests'] = {
    'title': _('Active Spot Fleet Requests'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_ec2_spot_fleet_total_target_capacity'] = {
    'title': _('Spot Fleet Requests Total Target Capacity'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_ec2_running_ondemand_instances_total'] = {
    'title': _('Total running On-Demand Instances'),
    'unit': 'count',
    'color': '#000000',
}

for i, inst_type in enumerate(AWSEC2InstTypes):
    metric_info['aws_ec2_running_ondemand_instances_%s' % inst_type] = {
        'title': _('Total running On-Demand %s Instances') % inst_type,
        'unit': 'count',
        'color': indexed_color(i, len(AWSEC2InstTypes)),
    }

for inst_fam in AWSEC2InstFamilies:
    metric_info['aws_ec2_running_ondemand_instances_%s_vcpu' % inst_fam[0]] = {
        'title': _('Total %s vCPUs') % AWSEC2InstFamilies[inst_fam],
        'unit': 'count',
        'color': '25/a',
    }

metric_info['aws_consumed_lcus'] = {
    'title': _('Consumed Load Balancer Capacity Units'),
    'unit': '',
    'color': '11/a',
}

metric_info['aws_active_connections'] = {
    'title': _('Active Connections'),
    'unit': '1/s',
    'color': '11/a',
}

metric_info['aws_active_tls_connections'] = {
    'title': _('Active TLS Connections'),
    'unit': '1/s',
    'color': '12/a',
}

metric_info['aws_new_connections'] = {
    'title': _('New Connections'),
    'unit': '1/s',
    'color': '13/a',
}

metric_info['aws_new_tls_connections'] = {
    'title': _('New TLS Connections'),
    'unit': '1/s',
    'color': '14/a',
}

metric_info['aws_rejected_connections'] = {
    'title': _('Rejected Connections'),
    'unit': '1/s',
    'color': '15/a',
}

metric_info['aws_client_tls_errors'] = {
    'title': _('Client TLS errors'),
    'unit': '1/s',
    'color': '21/a',
}

metric_info['aws_http_redirects'] = {
    'title': _('HTTP Redirects'),
    'unit': '1/s',
    'color': '11/a',
}

metric_info['aws_http_redirect_url_limit'] = {
    'title': _('HTTP Redirects URL Limit Exceeded'),
    'unit': '1/s',
    'color': '11/a',
}

metric_info['aws_http_fixed_response'] = {
    'title': _('HTTP Fixed Responses'),
    'unit': '1/s',
    'color': '11/a',
}

metric_info['aws_proc_bytes'] = {
    'title': _('Processed Bytes'),
    'unit': 'bytes/s',
    'color': '11/a',
}

metric_info['aws_proc_bytes_tls'] = {
    'title': _('TLS Processed Bytes'),
    'unit': 'bytes/s',
    'color': '12/a',
}

metric_info['aws_ipv6_proc_bytes'] = {
    'title': _('IPv6 Processed Bytes'),
    'unit': 'bytes/s',
    'color': '13/a',
}

metric_info['aws_ipv6_requests'] = {
    'title': _('IPv6 Requests'),
    'unit': '1/s',
    'color': '15/a',
}

metric_info['aws_rule_evaluations'] = {
    'title': _('Rule Evaluations'),
    'unit': '1/s',
    'color': '21/a',
}

metric_info['aws_failed_tls_client_handshake'] = {
    'title': _('Failed TLS Client Handshake'),
    'unit': '1/s',
    'color': '21/a',
}

metric_info['aws_failed_tls_target_handshake'] = {
    'title': _('Failed TLS Target Handshake'),
    'unit': '1/s',
    'color': '23/a',
}

metric_info['aws_tcp_client_rst'] = {
    'title': _('TCP Client Resets'),
    'unit': '1/s',
    'color': '31/a',
}

metric_info['aws_tcp_elb_rst'] = {
    'title': _('TCP ELB Resets'),
    'unit': '1/s',
    'color': '33/a',
}

metric_info['aws_tcp_target_rst'] = {
    'title': _('TCP Target Resets'),
    'unit': '1/s',
    'color': '35/a',
}

metric_info['aws_s3_downloads'] = {
    'title': _('Download'),
    'unit': 'bytes/s',
    'color': '21/a',
}

metric_info['aws_s3_uploads'] = {
    'title': _('Upload'),
    'unit': 'bytes/s',
    'color': '31/a',
}

metric_info['aws_s3_select_object_scanned'] = {
    'title': _('SELECT Object Scanned'),
    'unit': 'bytes/s',
    'color': '31/a',
}

metric_info['aws_s3_select_object_returned'] = {
    'title': _('SELECT Object Returned'),
    'unit': 'bytes/s',
    'color': '41/a',
}

metric_info['aws_s3_buckets'] = {
    'title': _('Buckets'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_elb_load_balancers'] = {
    'title': _('Load balancers'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_elb_load_balancer_listeners'] = {
    'title': _('Load balancer listeners'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_elb_load_balancer_registered_instances'] = {
    'title': _('Load balancer registered instances'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_rds_db_clusters'] = {
    'title': _('DB clusters'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_rds_db_cluster_parameter_groups'] = {
    'title': _('DB cluster parameter groups'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_rds_db_instances'] = {
    'title': _('DB instances'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_rds_event_subscriptions'] = {
    'title': _('Event subscriptions'),
    'unit': 'count',
    'color': '14/a',
}

metric_info['aws_rds_manual_snapshots'] = {
    'title': _('Manual snapshots'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_rds_option_groups'] = {
    'title': _('Option groups'),
    'unit': 'count',
    'color': '16/a',
}

metric_info['aws_rds_db_parameter_groups'] = {
    'title': _('DB parameter groups'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_rds_read_replica_per_master'] = {
    'title': _('Read replica per master'),
    'unit': 'count',
    'color': '22/a',
}

metric_info['aws_rds_reserved_db_instances'] = {
    'title': _('Reserved DB instances'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_rds_db_security_groups'] = {
    'title': _('DB security groups'),
    'unit': 'count',
    'color': '24/a',
}

metric_info['aws_rds_db_subnet_groups'] = {
    'title': _('DB subnet groups'),
    'unit': 'count',
    'color': '25/a',
}

metric_info['aws_rds_subnet_per_db_subnet_groups'] = {
    'title': _('Subnet per DB subnet groups'),
    'unit': 'count',
    'color': '26/a',
}

metric_info['aws_rds_allocated_storage'] = {
    'title': _('Allocated storage'),
    'unit': 'bytes',
    'color': '31/a',
}

metric_info['aws_rds_auths_per_db_security_groups'] = {
    'title': _('Authorizations per DB security group'),
    'unit': 'count',
    'color': '32/a',
}

metric_info['aws_rds_db_cluster_roles'] = {
    'title': _('DB cluster roles'),
    'unit': 'count',
    'color': '33/a',
}

metric_info['aws_ebs_block_store_snapshots'] = {
    'title': _('Block store snapshots'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_ebs_block_store_space_standard'] = {
    'title': _('Magnetic volumes space'),
    'unit': 'bytes',
    'color': '12/a',
}

metric_info['aws_ebs_block_store_space_io1'] = {
    'title': _('Provisioned IOPS SSD space'),
    'unit': 'bytes',
    'color': '13/a',
}

metric_info['aws_ebs_block_store_iops_io1'] = {
    'title': _('Provisioned IOPS SSD IO operations per second'),
    'unit': '1/s',
    'color': '14/a',
}

metric_info['aws_ebs_block_store_space_gp2'] = {
    'title': _('General Purpose SSD space'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_ebs_block_store_space_sc1'] = {
    'title': _('Cold HDD space'),
    'unit': 'bytes',
    'color': '16/a',
}

metric_info['aws_ebs_block_store_space_st1'] = {
    'title': _('Throughput Optimized HDD space'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_elbv2_application_load_balancers'] = {
    'title': _('Application Load balancers'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_elbv2_application_load_balancer_rules'] = {
    'title': _('Application Load Balancer Rules'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_elbv2_application_load_balancer_listeners'] = {
    'title': _('Application Load Balancer Listeners'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_elbv2_application_load_balancer_target_groups'] = {
    'title': _('Application Load Balancer Target Groups'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_elbv2_application_load_balancer_certificates'] = {
    'title': _('Application Load balancer Certificates'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_elbv2_network_load_balancers'] = {
    'title': _('Network Load balancers'),
    'unit': 'count',
    'color': '25/a',
}

metric_info['aws_elbv2_network_load_balancer_listeners'] = {
    'title': _('Network Load Balancer Listeners'),
    'unit': 'count',
    'color': '31/a',
}

metric_info['aws_elbv2_network_load_balancer_target_groups'] = {
    'title': _('Network Load Balancer Target Groups'),
    'unit': 'count',
    'color': '33/a',
}

metric_info['aws_elbv2_load_balancer_target_groups'] = {
    'title': _('Load balancers Target Groups'),
    'unit': 'count',
    'color': '35/a',
}

metric_info['aws_dynamodb_number_of_tables'] = {
    'title': _('Number of tables'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_dynamodb_read_capacity'] = {
    'title': _('Read Capacity'),
    'unit': 'RCU',
    'color': '16/a',
}

metric_info['aws_dynamodb_write_capacity'] = {
    'title': _('Write Capacity'),
    'unit': 'WCU',
    'color': '41/a',
}

metric_info['aws_dynamodb_consumed_rcu'] = {
    'title': _('Average consumption'),
    'unit': 'RCU',
    'color': '41/a',
}

metric_info['aws_dynamodb_consumed_rcu_perc'] = {
    'title': _('Average usage'),
    'unit': '%',
    'color': '41/a',
}

metric_info['aws_dynamodb_consumed_wcu'] = {
    'title': _('Average consumption'),
    'unit': 'RCU',
    'color': '41/a',
}

metric_info['aws_dynamodb_consumed_wcu_perc'] = {
    'title': _('Average usage'),
    'unit': '%',
    'color': '41/a',
}

metric_info['aws_dynamodb_minimum_consumed_rcu'] = {
    'title': _('Minimum single-request consumption'),
    'unit': 'RCU',
    'color': '31/b',
}

metric_info['aws_dynamodb_maximum_consumed_rcu'] = {
    'title': _('Maximum single-request consumption'),
    'unit': 'RCU',
    'color': '15/a',
}

metric_info['aws_dynamodb_minimum_consumed_wcu'] = {
    'title': _('Minimum single-request consumption'),
    'unit': 'RCU',
    'color': '31/b',
}

metric_info['aws_dynamodb_maximum_consumed_wcu'] = {
    'title': _('Maximum single-request consumption'),
    'unit': 'RCU',
    'color': '15/a',
}

metric_info['aws_dynamodb_query_average_latency'] = {
    'title': _('Average latency of successful Query requests'),
    'unit': 's',
    'color': '41/a',
}

metric_info['aws_dynamodb_query_maximum_latency'] = {
    'title': _('Maximum latency of successful Query requests'),
    'unit': 's',
    'color': '15/a',
}

metric_info['aws_dynamodb_getitem_average_latency'] = {
    'title': _('Average latency of successful GetItem requests'),
    'unit': 's',
    'color': '41/a',
}

metric_info['aws_dynamodb_getitem_maximum_latency'] = {
    'title': _('Maximum latency of successful GetItem requests'),
    'unit': 's',
    'color': '15/a',
}

metric_info['aws_dynamodb_putitem_average_latency'] = {
    'title': _('Average latency of successful PutItem requests'),
    'unit': 's',
    'color': '41/a',
}

metric_info['aws_dynamodb_putitem_maximum_latency'] = {
    'title': _('Maximum latency of successful PutItem requests'),
    'unit': 's',
    'color': '15/a',
}

metric_info['aws_wafv2_web_acls'] = {
    'title': _('Number of Web ACLs'),
    'unit': 'count',
    'color': '41/a',
}

metric_info['aws_wafv2_rule_groups'] = {
    'title': _('Number of rule groups'),
    'unit': 'count',
    'color': '16/a',
}

metric_info['aws_wafv2_ip_sets'] = {
    'title': _('Number of IP sets'),
    'unit': 'count',
    'color': '31/b',
}

metric_info['aws_wafv2_regex_pattern_sets'] = {
    'title': _('Number of regex sets'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_wafv2_web_acl_capacity_units'] = {
    'title': _('Web ACL capacity units (WCUs)'),
    'unit': 'count',
    'color': '41/a',
}

metric_info['aws_wafv2_requests_rate'] = {
    'title': _('Avg. request rate'),
    'unit': '1/s',
    'color': '#000000',
}

metric_info['aws_wafv2_allowed_requests_rate'] = {
    'title': _('Avg. rate of allowed requests'),
    'unit': '1/s',
    'color': '26/b',
}

metric_info['aws_wafv2_blocked_requests_rate'] = {
    'title': _('Avg. rate of blocked requests'),
    'unit': '1/s',
    'color': '16/a',
}

metric_info['aws_wafv2_allowed_requests_perc'] = {
    'title': _('Percentage of allowed requests'),
    'unit': '%',
    'color': '26/b',
}

metric_info['aws_wafv2_blocked_requests_perc'] = {
    'title': _('Percentage of blocked requests'),
    'unit': '%',
    'color': '16/a',
}

metric_info['aws_cloudwatch_alarms_cloudwatch_alarms'] = {
    'title': _('CloudWatch alarms'),
    'unit': 'count',
    'color': '41/a',
}

#.
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
    "title": _("Total running On-Demand Instances"),
    "metrics": [('aws_ec2_running_ondemand_instances_total', 'line')] +
               [('aws_ec2_running_ondemand_instances_%s' % inst_type, "stack")
                for inst_type in AWSEC2InstTypes],
    "optional_metrics": [
        'aws_ec2_running_ondemand_instances_%s' % inst_type for inst_type in AWSEC2InstTypes
    ],
}

graph_info['aws_http_nxx_errors_rate'] = {
    'title': _('HTTP 3/4/5XX Errors'),
    'metrics': [
        ('aws_http_2xx_rate', 'stack'),
        ('aws_http_3xx_rate', 'stack'),
        ('aws_http_4xx_rate', 'stack'),
        ('aws_http_5xx_rate', 'stack'),
    ],
    'optional_metrics': ['aws_http_2xx_rate', 'aws_http_3xx_rate'],
}
graph_info['aws_http_50x_errors_rate'] = {
    'title': _('HTTP 500/2/3/4 Errors'),
    'metrics': [
        ('aws_http_500_rate', 'stack'),
        ('aws_http_502_rate', 'stack'),
        ('aws_http_503_rate', 'stack'),
        ('aws_http_504_rate', 'stack'),
    ],
}
graph_info['aws_http_nxx_errors_perc'] = {
    'title': _('Percentage of HTTP 3/4/5XX Errors'),
    'metrics': [
        ('aws_http_2xx_perc', 'stack'),
        ('aws_http_3xx_perc', 'stack'),
        ('aws_http_4xx_perc', 'stack'),
        ('aws_http_5xx_perc', 'stack'),
    ],
    'optional_metrics': ['aws_http_2xx_perc', 'aws_http_3xx_perc'],
}
graph_info['aws_http_50x_errors_perc'] = {
    'title': _('Percentage of HTTP 500/2/3/4 Errors'),
    'metrics': [
        ('aws_http_500_perc', 'stack'),
        ('aws_http_502_perc', 'stack'),
        ('aws_http_503_perc', 'stack'),
        ('aws_http_504_perc', 'stack'),
    ],
}

graph_info['aws_dynamodb_read_capacity_single'] = {
    'title': _('Single-request consumption'),
    'metrics': [
        ('aws_dynamodb_minimum_consumed_rcu', 'line'),
        ('aws_dynamodb_maximum_consumed_rcu', 'line'),
    ],
}

graph_info['aws_dynamodb_write_capacity_single'] = {
    'title': _('Single-request consumption'),
    'metrics': [
        ('aws_dynamodb_minimum_consumed_wcu', 'line'),
        ('aws_dynamodb_maximum_consumed_wcu', 'line'),
    ],
}

graph_info['aws_dynamodb_query_latency'] = {
    'title': _('Latency of Query requests'),
    'metrics': [
        ('aws_dynamodb_query_average_latency', 'line'),
        ('aws_dynamodb_query_maximum_latency', 'line'),
    ],
}

graph_info['aws_dynamodb_getitem_latency'] = {
    'title': _('Latency of GetItem requests'),
    'metrics': [
        ('aws_dynamodb_getitem_average_latency', 'line'),
        ('aws_dynamodb_getitem_maximum_latency', 'line'),
    ],
}

graph_info['aws_dynamodb_putitem_latency'] = {
    'title': _('Latency of PutItem requests'),
    'metrics': [
        ('aws_dynamodb_putitem_average_latency', 'line'),
        ('aws_dynamodb_putitem_maximum_latency', 'line'),
    ],
}

graph_info['aws_wafv2_web_acl_requests'] = {
    'title': _('Web ACL Requests'),
    'metrics': [
        ('aws_wafv2_allowed_requests_rate', 'stack'),
        ('aws_wafv2_blocked_requests_rate', 'stack'),
        ('aws_wafv2_requests_rate', 'line'),
    ],
}
