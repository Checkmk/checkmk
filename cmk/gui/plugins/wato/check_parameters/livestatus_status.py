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
    Dictionary,
    MonitoringState,
    TextAscii,
    Tuple,
    Integer,
    Float,
    Percentage,
    Age,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_livestatus_status():
    return Dictionary(
        help=_("When monitoring the performance of a monitoring site (i.e. its core) "
               "then also settings are being checked, e.g. for manually disabled notifications. "
               "The status of the various situations can be configured here."),
        elements=[
            ("site_stopped", MonitoringState(title="State when the site is stopped",
                                             default_value=2)),
            ("execute_host_checks",
             MonitoringState(title="State when host checks are disabled", default_value=2)),
            ("execute_service_checks",
             MonitoringState(title="State when service checks are disabled", default_value=2)),
            ("accept_passive_host_checks",
             MonitoringState(title="State when not accepting passive host checks",
                             default_value=2)),
            ("accept_passive_service_checks",
             MonitoringState(title="State when not accepting passive service checks",
                             default_value=2)),
            ("check_host_freshness",
             MonitoringState(title="State when not checking host freshness", default_value=2)),
            ("check_service_freshness",
             MonitoringState(title="State when not checking service freshness", default_value=2)),
            ("enable_event_handlers",
             MonitoringState(title="State when event handlers are disabled", default_value=0)),
            ("enable_flap_detection",
             MonitoringState(title="State when flap detection is disabled", default_value=1)),
            ("enable_notifications",
             MonitoringState(title="State when notifications are disabled", default_value=2)),
            ("process_performance_data",
             MonitoringState(title="State when performance data is disabled", default_value=1)),
            ("check_external_commands",
             MonitoringState(title="State when not checking external commands", default_value=2)),
            ("site_cert_days",
             Tuple(
                 title=_("Site certificate validity"),
                 help=_("Minimum number of days a certificate has to be valid."),
                 elements=[
                     Integer(
                         title=_("Warning at or below"),
                         minvalue=0,
                         unit=_("days"),
                         default_value=30,
                     ),
                     Integer(
                         title=_("Critical at or below"),
                         minvalue=0,
                         unit=_("days"),
                         default_value=7,
                     ),
                 ],
             )),
            ("average_latency_generic",
             Tuple(title=_("Levels Latency Check"),
                   help=_("Set Levels for the Check Latency Time"),
                   elements=[
                       Age(
                           title=_("Warning at or above"),
                           default_value=30,
                       ),
                       Age(
                           title=_("Critical at or above"),
                           default_value=60,
                       ),
                   ])),
            ("average_latency_cmk",
             Tuple(title=_("Levels Latency Checkmk"),
                   help=_("Set Levels for the Checkmk Latency Time"),
                   elements=[
                       Age(
                           title=_("Warning at or above"),
                           default_value=30,
                       ),
                       Age(
                           title=_("Critical at or above"),
                           default_value=60,
                       ),
                   ])),
            ("helper_usage_generic",
             Tuple(title=_("Levels Helper usage Check"),
                   help=_("Set Levels for the Check helper Usage"),
                   elements=[
                       Percentage(
                           title=_("Warning at or above"),
                           default_value="60",
                       ),
                       Percentage(
                           title=_("Critical at or above"),
                           default_value="90",
                       ),
                   ])),
            ("helper_usage_cmk",
             Tuple(title=_("Levels Helper usage Checkmk"),
                   help=_("Set Levels for the Checkmk helper Usage"),
                   elements=[
                       Percentage(
                           title=_("Warning at or above"),
                           default_value="60",
                       ),
                       Percentage(
                           title=_("Critical at or above"),
                           default_value="90",
                       ),
                   ])),
            ("livestatus_usage",
             Tuple(title=_("Levels Livestatus Usage"),
                   help=_("Set Levels for the Checkmk Livestatus Usage"),
                   elements=[
                       Percentage(
                           title=_("Warning at or above"),
                           default_value="80",
                       ),
                       Percentage(
                           title=_("Critical at or above"),
                           default_value="90",
                       ),
                   ])),
            ("livestatus_overflows_rate",
             Tuple(title=_("Levels Livestatus Overflows"),
                   help=_("Set Levels for the Checkmk Livestatus Overflows"),
                   elements=[
                       Float(
                           title=_("Warning at or above"),
                           unit=_("/s"),
                           default_value="0.01",
                       ),
                       Float(
                           title=_("Critical at or above"),
                           unit=_("/s"),
                           default_value="0.02",
                       ),
                   ])),
            ("levels_hosts",
             Tuple(title=_("Levels Hosts"),
                   help=_("Set Levels for the number of Hosts"),
                   elements=[
                       Integer(
                           title=_("Warning at or above"),
                           unit=_("Hosts"),
                       ),
                       Integer(
                           title=_("Critical at or above"),
                           unit=_("Hosts"),
                       ),
                   ])),
            ("levels_services",
             Tuple(title=_("Levels Services"),
                   help=_("Set Levels for the number of Services"),
                   elements=[
                       Integer(
                           title=_("Warning at or above"),
                           unit=_("Services"),
                       ),
                       Integer(
                           title=_("Critical at or above"),
                           unit=_("Services"),
                       ),
                   ])),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="livestatus_status",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of the monitoring site"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_livestatus_status,
        title=lambda: _("Performance and settings of a Check_MK site"),
    ))
