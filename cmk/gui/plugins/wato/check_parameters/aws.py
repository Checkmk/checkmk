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
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_ec2_cpu_credits',
    _("AWS/EC2 CPU Credits"),
    Dictionary(elements=[('balance_levels_lower',
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
                              ]))]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_costs_and_usage',
    _("AWS Costs and Usage"),
    Dictionary(elements=[('levels_unblended',
                          Tuple(
                              title=_("Upper levels for unblended costs"),
                              elements=[
                                  Integer(title=_("Warning at")),
                                  Integer(title=_("Critical at")),
                              ]))]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_elb_statistics',
    _("AWS/ELB Statistics"),
    Dictionary(elements=[
        ('levels_surge_queue_length',
         Tuple(
             title=_("Upper levels for surge queue length"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ])),
        ('levels_spillover',
         Tuple(
             title=_("Upper levels for the number of requests that were rejected (spillover)"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_elb_latency',
    _("AWS/ELB Latency"),
    Dictionary(elements=[
        ('levels_latency',
         Tuple(
             title=_("Upper levels for latency"),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_elb_http',
    _("AWS/ELB HTTP Errors"),
    Dictionary(elements=[
        ('levels_http_4xx_perc',
         Tuple(
             title=_("Upper percentual levels for HTTP 400 errors"),
             help=_("Specify levels for HTTP 400 errors in percentage "
                    "which refer to the total number of requests"),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ])),
        ('levels_http_5xx_perc',
         Tuple(
             title=_("Upper percentual levels for HTTP 500 errors"),
             help=_("Specify levels for HTTP 500 errors in percentage "
                    "which refer to the total number of requests"),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_elb_healthy_hosts',
    _("AWS/ELB Healthy Hosts"),
    Dictionary(elements=[
        ('levels_overall_hosts_health_perc',
         Tuple(
             title=_("Upper percentual levels for healthy hosts"),
             help=_("These levels refer to the total number of instances or hosts "
                    "that are registered to the load balancer which is the sum of "
                    "healthy and unhealthy instances."),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'aws_elb_backend_connection_errors',
    _("AWS/ELB Backend Connection Errors"),
    Dictionary(elements=[
        ('levels_backend_connections_errors_rate',
         Tuple(
             title=_("Upper levels for backend connection errors per second"),
             elements=[
                 Float(title=_("Warning at")),
                 Float(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)
