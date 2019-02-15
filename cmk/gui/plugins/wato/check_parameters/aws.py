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
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _vs_s3_buckets():
    return ('bucket_size_levels',
            Alternative(
                title=_("Upper levels for the bucket size"),
                style="dropdown",
                elements=[
                    Tuple(
                        title=_("Set levels"),
                        elements=[
                            Filesize(title=_("Warning at")),
                            Filesize(title=_("Critical at")),
                        ]),
                    Tuple(
                        title=_("No levels"),
                        elements=[
                            FixedValue(None, totext=""),
                            FixedValue(None, totext=""),
                        ]),
                ]))


def _vs_burst_balance():
    return ('burst_balance_levels_lower',
            Alternative(
                title=_("Lower levels for burst balance"),
                style="dropdown",
                elements=[
                    Tuple(
                        title=_("Set levels"),
                        elements=[
                            Percentage(title=_("Warning at or below")),
                            Percentage(title=_("Critical at or below")),
                        ]),
                    Tuple(
                        title=_("No levels"),
                        elements=[
                            FixedValue(None, totext=""),
                            FixedValue(None, totext=""),
                        ]),
                ]))


def _vs_cpu_credits_balance():
    return ('balance_levels_lower',
            Alternative(
                title=_("Lower levels for CPU balance"),
                style="dropdown",
                elements=[
                    Tuple(
                        title=_("Set levels"),
                        elements=[
                            Integer(title=_("Warning at or below")),
                            Integer(title=_("Critical at or below")),
                        ]),
                    Tuple(
                        title=_("No levels"),
                        elements=[
                            FixedValue(None, totext=""),
                            FixedValue(None, totext=""),
                        ]),
                ]))


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
class RulespecCheckgroupParametersAwsCostsAndUsage(CheckParameterRulespecWithoutItem):
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
        return Dictionary(
            elements=[(
                'levels_unblended',
                Tuple(
                    title=_("Upper levels for unblended costs"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("USD per day")),
                        Integer(title=_("Critical at"), unit=_("USD per day")),
                    ],
                ),
            )],)


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
        return Dictionary(
            elements=[
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
                     title=_(
                         "Upper levels for the number of requests that were rejected (spillover)"),
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
        return Dictionary(
            elements=[(
                'levels_latency',
                Tuple(
                    title=_("Upper levels for latency"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            )],)


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
        return Dictionary(
            elements=[
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
                 Tuple(
                     title=_("Upper percentual levels for HTTP 500 errors"),
                     help=_("Specify levels for HTTP 500 errors in percentage "
                            "which refer to the total number of requests"),
                     elements=[
                         Percentage(title=_("Warning at")),
                         Percentage(title=_("Critical at")),
                     ])),
            ],)


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
        return Dictionary(
            elements=[(
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
        return Dictionary(
            elements=[(
                'levels_backend_connections_errors_rate',
                Tuple(
                    title=_("Upper levels for backend connection errors per second"),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            )],)


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
             Alternative(
                 title=_("Upper levels for disk usage"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Percentage(title=_("Warning at")),
                             Percentage(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
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
             Alternative(
                 title=_("Upper levels for connections in use"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Percentage(title=_("Warning at")),
                             Percentage(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
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
             Alternative(
                 title=_("Upper levels replica lag"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Age(title=_("Warning at")),
                             Age(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
                         elements=[
                             FixedValue(None, totext=""),
                             FixedValue(None, totext=""),
                         ]),
                 ])),
            ('slot_levels',
             Alternative(
                 title=_("Upper levels the oldest replication slot lag"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Filesize(title=_("Warning at")),
                             Filesize(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
                         elements=[
                             FixedValue(None, totext=""),
                             FixedValue(None, totext=""),
                         ]),
                 ])),
        ])

    @property
    def item_spec(self):
        return TextAscii(title=_("Database identifier"))
