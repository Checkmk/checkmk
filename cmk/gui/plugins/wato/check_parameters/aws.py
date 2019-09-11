#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    Integer,
    Tuple,
    Float,
    Percentage,
    Age,
    FixedValue,
    TextAscii,
    Filesize,
    ListOf,
    CascadingDropdown,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)
from cmk.special_agents.agent_aws import (
    AWSEC2InstTypes,
    AWSEC2LimitsDefault,
    AWSEC2LimitsSpecial,
)


def _vs_s3_buckets():
    return ('bucket_size_levels',
            Alternative(title=_("Upper levels for the bucket size"),
                        style="dropdown",
                        elements=[
                            Tuple(title=_("Set levels"),
                                  elements=[
                                      Filesize(title=_("Warning at")),
                                      Filesize(title=_("Critical at")),
                                  ]),
                            Tuple(title=_("No levels"),
                                  elements=[
                                      FixedValue(None, totext=""),
                                      FixedValue(None, totext=""),
                                  ]),
                        ]))


def _vs_glacier_vaults():
    return ('vault_size_levels',
            Alternative(title=_("Upper levels for the vault size"),
                        style="dropdown",
                        elements=[
                            Tuple(title=_("Set levels"),
                                  elements=[
                                      Filesize(title=_("Warning at")),
                                      Filesize(title=_("Critical at")),
                                  ]),
                            Tuple(title=_("No levels"),
                                  elements=[
                                      FixedValue(None, totext=""),
                                      FixedValue(None, totext=""),
                                  ]),
                        ]))


def _vs_burst_balance():
    return ('burst_balance_levels_lower',
            Alternative(title=_("Lower levels for burst balance"),
                        style="dropdown",
                        elements=[
                            Tuple(title=_("Set levels"),
                                  elements=[
                                      Percentage(title=_("Warning at or below")),
                                      Percentage(title=_("Critical at or below")),
                                  ]),
                            Tuple(title=_("No levels"),
                                  elements=[
                                      FixedValue(None, totext=""),
                                      FixedValue(None, totext=""),
                                  ]),
                        ]))


def _vs_cpu_credits_balance():
    return ('balance_levels_lower',
            Alternative(title=_("Lower levels for CPU balance"),
                        style="dropdown",
                        elements=[
                            Tuple(title=_("Set levels"),
                                  elements=[
                                      Integer(title=_("Warning at or below")),
                                      Integer(title=_("Critical at or below")),
                                  ]),
                            Tuple(title=_("No levels"),
                                  elements=[
                                      FixedValue(None, totext=""),
                                      FixedValue(None, totext=""),
                                  ]),
                        ]))


def _vs_elements_http_errors():
    return [
        ('levels_http_4xx_perc',
         Tuple(
             title=_("Upper percentual levels for HTTP 400 errors"),
             help=_("Specify levels for HTTP 400 errors in percentage "
                    "which refer to the total number of requests"),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ],
         )),
        ('levels_http_5xx_perc',
         Tuple(title=_("Upper percentual levels for HTTP 500 errors"),
               help=_("Specify levels for HTTP 500 errors in percentage "
                      "which refer to the total number of requests"),
               elements=[
                   Percentage(title=_("Warning at")),
                   Percentage(title=_("Critical at")),
               ])),
    ]


def _vs_latency():
    return ('levels_latency',
            Tuple(
                title=_("Upper levels for latency"),
                elements=[
                    Age(title=_("Warning at")),
                    Age(title=_("Critical at")),
                ],
            ))


def _vs_limits(resource, default_limit, vs_limit_cls=None):
    if vs_limit_cls is None:
        vs_limit = Integer(unit=_("%s" % resource), min_value=1, default_value=default_limit)
    else:
        vs_limit = vs_limit_cls(min_value=1, default_value=default_limit)

    if resource:
        title = _("Set limit and levels for %s" % resource)
    else:
        title = None
    return Alternative(
        title=title,
        style="dropdown",
        elements=[
            Tuple(
                title=_("Set levels"),
                elements=[
                    Alternative(elements=[FixedValue(None, totext="Limit from AWS API"), vs_limit]),
                    Percentage(title=_("Warning at"), default_value=80.0),
                    Percentage(title=_("Critical at"), default_value=90.0),
                ]),
            Tuple(title=_("No levels"),
                  elements=[
                      FixedValue(None, totext=""),
                      FixedValue(None, totext=""),
                      FixedValue(None, totext=""),
                  ]),
        ])


#.
#   .--Glacier-------------------------------------------------------------.
#   |                    ____ _            _                               |
#   |                   / ___| | __ _  ___(_) ___ _ __                     |
#   |                  | |  _| |/ _` |/ __| |/ _ \ '__|                    |
#   |                  | |_| | | (_| | (__| |  __/ |                       |
#   |                   \____|_|\__,_|\___|_|\___|_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_glacier_vault_archives():
    return TextAscii(title=_("The vault name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_glacier_vault_archives",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_glacier_vault_archives,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_glacier_vaults()]),
        title=lambda: _("AWS/Glacier Vault Objects"),
    ))


def _parameter_valuespec_aws_glacier_vaults():
    return Dictionary(elements=[_vs_glacier_vaults()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_glacier_vaults",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_glacier_vaults,
        title=lambda: _("AWS/Glacier Vaults"),
    ))


def _parameter_valuespec_aws_glacier_limits():
    return Dictionary(elements=[('number_of_vaults', _vs_limits("Vaults", 1000))])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_glacier_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_glacier_limits,
        title=lambda: _("AWS/Glacier Limits"),
    ))

#.
#   .--S3------------------------------------------------------------------.
#   |                             ____ _____                               |
#   |                            / ___|___ /                               |
#   |                            \___ \ |_ \                               |
#   |                             ___) |__) |                              |
#   |                            |____/____/                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_s3_buckets_objects():
    return TextAscii(title=_("The bucket name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_buckets_objects",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_buckets_objects,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_s3_buckets()]),
        title=lambda: _("AWS/S3 Bucket Objects"),
    ))


def _parameter_valuespec_aws_s3_buckets():
    return Dictionary(elements=[_vs_s3_buckets()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_s3_buckets",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_buckets,
        title=lambda: _("AWS/S3 Buckets"),
    ))


def _item_spec_aws_s3_requests():
    return TextAscii(title=_("The bucket name"))


def _parameter_valuespec_aws_s3_requests():
    return Dictionary(elements=[
        ('get_requests_perc',
         Alternative(title=_("Upper percentual levels for GET requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('put_requests_perc',
         Alternative(title=_("Upper percentual levels for PUT requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('delete_requests_perc',
         Alternative(title=_("Upper percentual levels for DELETE requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('head_requests_perc',
         Alternative(title=_("Upper percentual levels for HEAD requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('post_requests_perc',
         Alternative(title=_("Upper percentual levels for POST requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('select_requests_perc',
         Alternative(title=_("Upper percentual levels for SELECT requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('list_requests_perc',
         Alternative(title=_("Upper percentual levels for LIST requests"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_requests",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_requests,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_requests,
        title=lambda: _("AWS/S3 Bucket Requests"),
    ))


def _item_spec_aws_s3_latency():
    return TextAscii(title=_("The bucket name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_latency",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_latency,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_latency()]),
        title=lambda: _("AWS/S3 Latency"),
    ))


def _parameter_valuespec_aws_s3_limits():
    return Dictionary(elements=[('buckets', _vs_limits("Buckets", 100))])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_s3_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_limits,
        title=lambda: _("AWS/S3 Limits"),
    ))

#.
#   .--EC2-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___|___ \                            |
#   |                         |  _|| |     __) |                           |
#   |                         | |__| |___ / __/                            |
#   |                         |_____\____|_____|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_valuespec_aws_ec2_cpu_credits():
    return Dictionary(elements=[_vs_cpu_credits_balance()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_ec2_cpu_credits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_ec2_cpu_credits,
        title=lambda: _("AWS/EC2 CPU Credits"),
    ))


def _vs_limits_inst_types():
    return ListOf(
        CascadingDropdown(orientation="horizontal",
                          choices=[(inst_type, inst_type,
                                    _vs_limits(
                                        "%s instances" % inst_type,
                                        AWSEC2LimitsSpecial.get(inst_type, AWSEC2LimitsDefault)[0]))
                                   for inst_type in AWSEC2InstTypes]),
        title=_("Set limits and levels for running on-demand instances"),
    )


def _parameter_valuespec_aws_ec2_limits():
    return Dictionary(elements=[
        ('vpc_elastic_ip_addresses', _vs_limits("VPC Elastic IP Addresses", 5)),
        ('elastic_ip_addresses', _vs_limits("Elastic IP Addresses", 5)),
        ('vpc_sec_group_rules', _vs_limits("Rules of VPC security group", 50)),
        ('vpc_sec_groups', _vs_limits("Security Groups of VPC", 500)),
        ('if_vpc_sec_group', _vs_limits("VPC security groups of elastic network interface", 5)),
        ('spot_inst_requests', _vs_limits("Spot Instance Requests", 20)),
        ('active_spot_fleet_requests', _vs_limits("Active Spot Fleet Requests", 1000)),
        ('spot_fleet_total_target_capacity',
         _vs_limits("Spot Fleet Requests Total Target Capacity", 5000)),
        ('running_ondemand_instances_total', _vs_limits("Total Running On-Demand Instances", 20)),
        ('running_ondemand_instances', _vs_limits_inst_types()),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_ec2_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_ec2_limits,
        title=lambda: _("AWS/EC2 Limits"),
    ))

#.
#   .--CE------------------------------------------------------------------.
#   |                              ____ _____                              |
#   |                             / ___| ____|                             |
#   |                            | |   |  _|                               |
#   |                            | |___| |___                              |
#   |                             \____|_____|                             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_costs_and_usage():
    return TextAscii(title=_("The service name"))


def _parameter_valuespec_aws_costs_and_usage():
    return Dictionary(elements=[(
        'levels_unblended',
        Tuple(
            title=_("Upper levels for unblended costs"),
            elements=[
                Integer(title=_("Warning at"), unit=_("USD per day")),
                Integer(title=_("Critical at"), unit=_("USD per day")),
            ],
        ),
    )],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_costs_and_usage",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_costs_and_usage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_costs_and_usage,
        title=lambda: _("AWS/CE Costs and Usage"),
    ))

#.
#   .--ELB-----------------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_valuespec_aws_elb_statistics():
    return Dictionary(elements=[
        ('levels_surge_queue_length',
         Tuple(
             title=_("Upper levels for surge queue length"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ('levels_spillover',
         Tuple(
             title=_("Upper levels for the number of requests that were rejected (spillover)"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_statistics",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_statistics,
        title=lambda: _("AWS/ELB Statistics"),
    ))


def _parameter_valuespec_aws_elb_latency():
    return Dictionary(elements=[_vs_latency()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_latency",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_latency,
        title=lambda: _("AWS/ELB Latency"),
    ))


def _parameter_valuespec_aws_elb_http():
    return Dictionary(elements=_vs_elements_http_errors())


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_http",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_http,
        title=lambda: _("AWS/ELB HTTP Errors"),
    ))


def _parameter_valuespec_aws_elb_healthy_hosts():
    return Dictionary(elements=[(
        'levels_overall_hosts_health_perc',
        Tuple(
            title=_("Upper percentual levels for healthy hosts"),
            help=_("These levels refer to the total number of instances or hosts "
                   "that are registered to the load balancer which is the sum of "
                   "healthy and unhealthy instances."),
            elements=[
                Percentage(title=_("Warning at")),
                Percentage(title=_("Critical at")),
            ],
        ),
    )],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_healthy_hosts",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_healthy_hosts,
        title=lambda: _("AWS/ELB Healthy Hosts"),
    ))


def _parameter_valuespec_aws_elb_backend_connection_errors():
    return Dictionary(elements=[(
        'levels_backend_connections_errors_rate',
        Tuple(
            title=_("Upper levels for backend connection errors per second"),
            elements=[
                Float(title=_("Warning at")),
                Float(title=_("Critical at")),
            ],
        ),
    )],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_backend_connection_errors",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_backend_connection_errors,
        title=lambda: _("AWS/ELB Backend Connection Errors"),
    ))


def _parameter_valuespec_aws_elb_limits():
    return Dictionary(elements=[
        ('load_balancers', _vs_limits("Load balancers", 20)),
        ('load_balancer_listeners', _vs_limits("Listeners per load balancer", 100)),
        ('load_balancer_registered_instances',
         _vs_limits("Registered instances per load balancer", 1000)),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_limits,
        title=lambda: _("AWS/ELB Limits"),
    ))

#.
#   .--ELBv2---------------------------------------------------------------.
#   |                    _____ _     ____       ____                       |
#   |                   | ____| |   | __ )_   _|___ \                      |
#   |                   |  _| | |   |  _ \ \ / / __) |                     |
#   |                   | |___| |___| |_) \ V / / __/                      |
#   |                   |_____|_____|____/ \_/ |_____|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_valuespec_aws_elbv2_limits():
    return Dictionary(elements=[
        ('application_load_balancers', _vs_limits("Application Load balancers", 20)),
        ('application_load_balancer_rules', _vs_limits("Application Load Balancer Rules", 100)),
        ('application_load_balancer_listeners',
         _vs_limits("Application Load Balancer Listeners", 50)),
        ('application_load_balancer_target_groups',
         _vs_limits("Application Load Balancer Target Groups", 3000)),
        ('application_load_balancer_certificates',
         _vs_limits("Application Load balancer Certificates", 25)),
        ('network_load_balancers', _vs_limits("Network Load balancers", 20)),
        ('network_load_balancer_listeners', _vs_limits("Network Load Balancer Listeners", 50)),
        ('network_load_balancer_target_groups',
         _vs_limits("Network Load Balancer Target Groups", 3000)),
        ('load_balancer_target_groups', _vs_limits("Load balancers Target Groups", 3000)),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elbv2_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elbv2_limits,
        title=lambda: _("AWS/ELBv2 Limits"),
    ))


def _parameter_valuespec_aws_elbv2_lcu():
    return Dictionary(elements=[
        ('levels',
         Tuple(title=_('Upper levels for load balancer capacity units'),
               elements=[
                   Float(title=_('Warning at')),
                   Float(title=_('Critical at')),
               ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elbv2_lcu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elbv2_lcu,
        title=lambda: _("AWS/ELBv2 LCU"),
    ))

#.
#   .--EBS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____| __ ) ___|                            |
#   |                         |  _| |  _ \___ \                            |
#   |                         | |___| |_) |__) |                           |
#   |                         |_____|____/____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_ebs_burst_balance():
    return TextAscii(title=_("Block storage name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_ebs_burst_balance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_ebs_burst_balance,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_burst_balance()]),
        title=lambda: _("AWS/EBS Burst Balance"),
    ))


def _parameter_valuespec_aws_ebs_limits():
    return Dictionary(elements=[
        ('block_store_snapshots', _vs_limits("Total Block store snapshots", 100000)),
        ('block_store_space_standard',
         _vs_limits("Total Magnetic volumes space", 300 * 1024**4, vs_limit_cls=Filesize)),
        ('block_store_space_io1',
         _vs_limits("Total Provisioned IOPS SSD space", 300 * 1024**4, vs_limit_cls=Filesize)),
        ('block_store_iops_io1',
         _vs_limits("Total Provisioned IOPS SSD IO operations per seconds", 300000)),
        ('block_store_space_gp2',
         _vs_limits("Total General Purpose SSD space", 300 * 1024**4, vs_limit_cls=Filesize)),
        ('block_store_space_sc1',
         _vs_limits("Total Cold HDD space", 300 * 1024**4, vs_limit_cls=Filesize)),
        ('block_store_space_st1',
         _vs_limits("Total Throughput Optimized HDD space", 300 * 1024**4, vs_limit_cls=Filesize)),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_ebs_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_ebs_limits,
        title=lambda: _("AWS/EBS Limits"),
    ))

#.
#   .--RDS-----------------------------------------------------------------.
#   |                          ____  ____  ____                            |
#   |                         |  _ \|  _ \/ ___|                           |
#   |                         | |_) | | | \___ \                           |
#   |                         |  _ <| |_| |___) |                          |
#   |                         |_| \_\____/|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_rds_cpu_credits():
    return TextAscii(title=_("Database identifier"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_cpu_credits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds_cpu_credits,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(
            elements=[_vs_cpu_credits_balance(), _vs_burst_balance()]),
        title=lambda: _("AWS/RDS CPU Credits"),
    ))


def _item_spec_aws_rds_disk_usage():
    return TextAscii(title=_("Database identifier"))


def _parameter_valuespec_aws_rds_disk_usage():
    return Dictionary(elements=[
        ('levels',
         Alternative(title=_("Upper levels for disk usage"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_disk_usage",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds_disk_usage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_disk_usage,
        title=lambda: _("AWS/RDS Disk Usage"),
    ))


def _item_spec_aws_rds_connections():
    return TextAscii(title=_("Database identifier"))


def _parameter_valuespec_aws_rds_connections():
    return Dictionary(elements=[
        ('levels',
         Alternative(title=_("Upper levels for connections in use"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Integer(title=_("Warning at")),
                                   Integer(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds_connections,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_connections,
        title=lambda: _("AWS/RDS Connections"),
    ))


def _item_spec_aws_rds_replica_lag():
    return TextAscii(title=_("Database identifier"))


def _parameter_valuespec_aws_rds_replica_lag():
    return Dictionary(elements=[
        ('lag_levels',
         Alternative(title=_("Upper levels replica lag"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Age(title=_("Warning at")),
                                   Age(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('slot_levels',
         Alternative(title=_("Upper levels the oldest replication slot lag"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Filesize(title=_("Warning at")),
                                   Filesize(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_replica_lag",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds_replica_lag,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_replica_lag,
        title=lambda: _("AWS/RDS Replica lag"),
    ))


def _parameter_valuespec_aws_rds_limits():
    return Dictionary(elements=[
        ('db_instances', _vs_limits("DB instances", 40)),
        ('reserved_db_instances', _vs_limits("Reserved DB instances", 40)),
        ('allocated_storage',
         _vs_limits("Allocated storage", 100 * 1024**4, vs_limit_cls=Filesize)),
        ('db_security_groups', _vs_limits("DB security groups", 25)),
        ('auths_per_db_security_groups', _vs_limits("Authorizations per DB security group", 20)),
        ('db_parameter_groups', _vs_limits("DB parameter groups", 50)),
        ('manual_snapshots', _vs_limits("Manual snapshots", 100)),
        ('event_subscriptions', _vs_limits("Event subscriptions", 20)),
        ('db_subnet_groups', _vs_limits("DB subnet groups", 50)),
        ('option_groups', _vs_limits("Option groups", 20)),
        ('subnet_per_db_subnet_groups', _vs_limits("Subnet per DB subnet groups", 20)),
        ('read_replica_per_master', _vs_limits("Read replica per master", 5)),
        ('db_clusters', _vs_limits("DB clusters", 40)),
        ('db_cluster_parameter_groups', _vs_limits("DB cluster parameter groups", 50)),
        ('db_cluster_roles', _vs_limits("DB cluster roles", 5)),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_rds_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_limits,
        title=lambda: _("AWS/RDS Limits"),
    ))

#.
#   .--Cloudwatch----------------------------------------------------------.
#   |         ____ _                 _               _       _             |
#   |        / ___| | ___  _   _  __| |_      ____ _| |_ ___| |__          |
#   |       | |   | |/ _ \| | | |/ _` \ \ /\ / / _` | __/ __| '_ \         |
#   |       | |___| | (_) | |_| | (_| |\ V  V / (_| | || (__| | | |        |
#   |        \____|_|\___/ \__,_|\__,_| \_/\_/ \__,_|\__\___|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_valuespec_aws_cloudwatch_alarms_limits():
    return Dictionary(elements=[
        ('cloudwatch_alarms', _vs_limits("Cloudwatch Alarms", 5000)),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_cloudwatch_alarms_limits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_cloudwatch_alarms_limits,
        title=lambda: _("AWS/Cloudwatch Alarms Limits"),
    ))
