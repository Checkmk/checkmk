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


@rulespec_registry.register
class RulespecCheckgroupParametersAwsGlacierVaultArchives(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_glacier_vault_archives"

    @property
    def title(self):
        return _("AWS/Glacier Vault Objects")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_glacier_vaults()])

    @property
    def item_spec(self):
        return TextAscii(title=_("The vault name"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsGlacierVaults(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_glacier_vaults"

    @property
    def title(self):
        return _("AWS/Glacier Vaults")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_glacier_vaults()])


@rulespec_registry.register
class RulespecCheckgroupParametersAwsGlacierLimits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_glacier_limits"

    @property
    def title(self):
        return _("AWS/Glacier Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[('number_of_vaults', _vs_limits("Vaults", 1000))])


#.
#   .--S3------------------------------------------------------------------.
#   |                             ____ _____                               |
#   |                            / ___|___ /                               |
#   |                            \___ \ |_ \                               |
#   |                             ___) |__) |                              |
#   |                            |____/____/                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsS3BucketsObjects(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_s3_buckets_objects"

    @property
    def title(self):
        return _("AWS/S3 Bucket Objects")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_s3_buckets()])

    @property
    def item_spec(self):
        return TextAscii(title=_("The bucket name"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsS3Buckets(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_s3_buckets"

    @property
    def title(self):
        return _("AWS/S3 Buckets")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_s3_buckets()])


@rulespec_registry.register
class RulespecCheckgroupParametersAwsS3Requests(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_s3_requests"

    @property
    def title(self):
        return _("AWS/S3 Bucket Requests")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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

    @property
    def item_spec(self):
        return TextAscii(title=_("The bucket name"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsS3Latency(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_s3_latency"

    @property
    def title(self):
        return _("AWS/S3 Latency")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_latency()])

    @property
    def item_spec(self):
        return TextAscii(title=_("The bucket name"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsS3Limits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_s3_limits"

    @property
    def title(self):
        return _("AWS/S3 Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[('buckets', _vs_limits("Buckets", 100))])


#.
#   .--EC2-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___|___ \                            |
#   |                         |  _|| |     __) |                           |
#   |                         | |__| |___ / __/                            |
#   |                         |_____\____|_____|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsEc2CpuCredits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_ec2_cpu_credits"

    @property
    def title(self):
        return _("AWS/EC2 CPU Credits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_cpu_credits_balance()])


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


@rulespec_registry.register
class RulespecCheckgroupParametersAwsEc2Limits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_ec2_limits"

    @property
    def title(self):
        return _("AWS/EC2 Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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
            ('running_ondemand_instances_total',
             _vs_limits("Total Running On-Demand Instances", 20)),
            ('running_ondemand_instances', _vs_limits_inst_types()),
        ])


#.
#   .--CE------------------------------------------------------------------.
#   |                              ____ _____                              |
#   |                             / ___| ____|                             |
#   |                            | |   |  _|                               |
#   |                            | |___| |___                              |
#   |                             \____|_____|                             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsCostsAndUsage(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_costs_and_usage"

    @property
    def title(self):
        return _("AWS/CE Costs and Usage")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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

    @property
    def item_spec(self):
        return TextAscii(title=_("The service name"))


#.
#   .--ELB-----------------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbStatistics(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elb_statistics"

    @property
    def title(self):
        return _("AWS/ELB Statistics")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbLatency(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elb_latency"

    @property
    def title(self):
        return _("AWS/ELB Latency")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_latency()])


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbHttp(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elb_http"

    @property
    def title(self):
        return _("AWS/ELB HTTP Errors")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=_vs_elements_http_errors())


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbHealthyHosts(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elb_healthy_hosts"

    @property
    def title(self):
        return _("AWS/ELB Healthy Hosts")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbBackendConnectionErrors(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elb_backend_connection_errors"

    @property
    def title(self):
        return _("AWS/ELB Backend Connection Errors")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbLimits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elb_limits"

    @property
    def title(self):
        return _("AWS/ELB Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ('load_balancers', _vs_limits("Load balancers", 20)),
            ('load_balancer_listeners', _vs_limits("Listeners per load balancer", 100)),
            ('load_balancer_registered_instances',
             _vs_limits("Registered instances per load balancer", 1000)),
        ])


#.
#   .--ELBv2---------------------------------------------------------------.
#   |                    _____ _     ____       ____                       |
#   |                   | ____| |   | __ )_   _|___ \                      |
#   |                   |  _| | |   |  _ \ \ / / __) |                     |
#   |                   | |___| |___| |_) \ V / / __/                      |
#   |                   |_____|_____|____/ \_/ |_____|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbv2Limits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elbv2_limits"

    @property
    def title(self):
        return _("AWS/ELBv2 Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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


@rulespec_registry.register
class RulespecCheckgroupParametersAwsElbv2LCU(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_elbv2_lcu"

    @property
    def title(self):
        return _("AWS/ELBv2 LCU")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ('levels',
             Tuple(title=_('Upper levels for load balancer capacity units'),
                   elements=[
                       Float(title=_('Warning at')),
                       Float(title=_('Critical at')),
                   ])),
        ])


#.
#   .--EBS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____| __ ) ___|                            |
#   |                         |  _| |  _ \___ \                            |
#   |                         | |___| |_) |__) |                           |
#   |                         |_____|____/____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsEbsBurstBalance(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_ebs_burst_balance"

    @property
    def title(self):
        return _("AWS/EBS Burst Balance")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_burst_balance()])

    @property
    def item_spec(self):
        return TextAscii(title=_("Block storage name"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsEbsLimits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_ebs_limits"

    @property
    def title(self):
        return _("AWS/EBS Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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
             _vs_limits(
                 "Total Throughput Optimized HDD space", 300 * 1024**4, vs_limit_cls=Filesize)),
        ])


#.
#   .--RDS-----------------------------------------------------------------.
#   |                          ____  ____  ____                            |
#   |                         |  _ \|  _ \/ ___|                           |
#   |                         | |_) | | | \___ \                           |
#   |                         |  _ <| |_| |___) |                          |
#   |                         |_| \_\____/|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsRdsCpuCredits(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_rds_cpu_credits"

    @property
    def title(self):
        return _("AWS/RDS CPU Credits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[_vs_cpu_credits_balance(), _vs_burst_balance()])

    @property
    def item_spec(self):
        return TextAscii(title=_("Database identifier"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsRdsDiskUsage(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_rds_disk_usage"

    @property
    def title(self):
        return _("AWS/RDS Disk Usage")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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

    @property
    def item_spec(self):
        return TextAscii(title=_("Database identifier"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsRdsConnections(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_rds_connections"

    @property
    def title(self):
        return _("AWS/RDS Connections")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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

    @property
    def item_spec(self):
        return TextAscii(title=_("Database identifier"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsRdsReplicaLag(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_rds_replica_lag"

    @property
    def title(self):
        return _("AWS/RDS Replica lag")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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

    @property
    def item_spec(self):
        return TextAscii(title=_("Database identifier"))


@rulespec_registry.register
class RulespecCheckgroupParametersAwsRdsLimits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_rds_limits"

    @property
    def title(self):
        return _("AWS/RDS Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ('db_instances', _vs_limits("DB instances", 40)),
            ('reserved_db_instances', _vs_limits("Reserved DB instances", 40)),
            ('allocated_storage',
             _vs_limits("Allocated storage", 100 * 1024**4, vs_limit_cls=Filesize)),
            ('db_security_groups', _vs_limits("DB security groups", 25)),
            ('auths_per_db_security_groups',
             _vs_limits("Authorizations per DB security group", 20)),
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


#.
#   .--Cloudwatch----------------------------------------------------------.
#   |         ____ _                 _               _       _             |
#   |        / ___| | ___  _   _  __| |_      ____ _| |_ ___| |__          |
#   |       | |   | |/ _ \| | | |/ _` \ \ /\ / / _` | __/ __| '_ \         |
#   |       | |___| | (_) | |_| | (_| |\ V  V / (_| | || (__| | | |        |
#   |        \____|_|\___/ \__,_|\__,_| \_/\_/ \__,_|\__\___|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@rulespec_registry.register
class RulespecCheckgroupParametersAwsCloudwatchAlarmsLimits(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "aws_cloudwatch_alarms_limits"

    @property
    def title(self):
        return _("AWS/Cloudwatch Alarms Limits")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ('cloudwatch_alarms', _vs_limits("Cloudwatch Alarms", 5000)),
        ])
