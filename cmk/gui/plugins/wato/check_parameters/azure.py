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
    Float,
    Integer,
    MonitoringState,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "azure_agent_info",
    ("Azure Agent Info"),
    Dictionary(elements=[
        ("warning_levels",
         Tuple(
             title=_("Upper levels for encountered warnings"),
             elements=[
                 Integer(title=_("Warning at"), default_value=1),
                 Integer(title=_("Critical at"), default_value=10),
             ],
         )),
        ("exception_levels",
         Tuple(
             title=_("Upper levels for encountered exceptions"),
             elements=[
                 Integer(title=_("Warning at"), default_value=1),
                 Integer(title=_("Critical at"), default_value=1),
             ],
         )),
        ("remaining_reads_levels_lower",
         Tuple(
             title=_("Lower levels for remaining API reads"),
             elements=[
                 Integer(title=_("Warning below"), default_value=1000),
                 Integer(title=_("Critical below"), default_value=100),
             ],
         )),
        ("remaining_reads_unknown_state",
         MonitoringState(title=_("State if remaining API reads are unknown"), default_value=1)),
    ]),
    TextAscii(title=_("Azure Agent Info")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "webserver",
    _("Azure web servers (IIS)"),
    Dictionary(
        elements=[
            (
                "avg_response_time_levels",
                Tuple(
                    title=_("Upper levels for average response time"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.00, unit="s"),
                        Float(title=_("Critical at"), default_value=10.0, unit="s"),
                    ]),
            ),
            (
                "error_rate_levels",
                Tuple(
                    title=_("Upper levels for rate of server errors"),
                    elements=[
                        Float(title=_("Warning at"), default_value=0.01, unit="1/s"),
                        Float(title=_("Critical at"), default_value=0.04, unit="1/s"),
                    ]),
            ),
            (
                "cpu_time_percent_levels",
                Tuple(
                    title=_("Upper levels for CPU time"),
                    elements=[
                        Float(title=_("Warning at"), default_value=85., unit="%"),
                        Float(title=_("Critical at"), default_value=95., unit="%"),
                    ]),
            ),
        ],),
    TextAscii(title=_("Name of the service")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'azure_storageaccounts',
    _("Azure Storage"),
    Dictionary(elements=[
        ('ingress_levels',
         Tuple(
             title=_("Levels on ingress data in bytes"),
             elements=[
                 Float(title=_("Warning at"), unit="B"),
                 Float(title=_("Critical at"), unit="B"),
             ],
         )),
        ('egress_levels',
         Tuple(
             title=_("Levels on ingress data in bytes"),
             elements=[
                 Float(title=_("Warning at"), unit="B"),
                 Float(title=_("Critical at"), unit="B"),
             ],
         )),
        ('used_capacity_levels',
         Tuple(
             title=_("Levels on used capacity in bytes"),
             elements=[
                 Float(title=_("Warning at"), unit="B"),
                 Float(title=_("Critical at"), unit="B"),
             ],
         )),
        ('server_latency_levels',
         Tuple(
             title=_("Levels on server latency in seconds"),
             help=_("Average latency used by Azure Storage to process a successful request"),
             elements=[
                 Float(title=_("Warning at"), unit="s"),
                 Float(title=_("Critical at"), unit="s"),
             ],
         )),
        ('e2e_latency_levels',
         Tuple(
             title=_("Levels on end-to-end latency in seconds"),
             help=_("Average end-to-end latency of successful requests made to a storage service"),
             elements=[
                 Float(title=_("Warning at"), unit="s"),
                 Float(title=_("Critical at"), unit="s"),
             ],
         )),
        ('transactions_levels',
         Tuple(
             title=_("Levels on transaction count"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ('availability_levels',
         Tuple(
             title=_("Levels on availability in percent"),
             elements=[
                 Float(title=_("Warning at"), unit="%"),
                 Float(title=_("Critical at"), unit="%"),
             ],
         )),
    ]),
    TextAscii(
        title=_("Storage account name"),
        help=_("Specify storage account names that the rule should apply to"),
    ),
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'azure_databases',
    _("Azure Databases"),
    Dictionary(
        title=_("Set Levels"),
        elements=[
            ('storage_percent_levels',
             Tuple(
                 title=_("Used storage in percent"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('%'), default_value=85.0),
                     Float(title=_("Critical at"), unit=_('%'), default_value=95.0)
                 ])),
            ('cpu_percent_levels',
             Tuple(
                 title=_("CPU in percent"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('%'), default_value=85.0),
                     Float(title=_("Critical at"), unit=_('%'), default_value=95.0)
                 ])),
            ('dtu_percent_levels',
             Tuple(
                 title=_("Database throughput units in percent"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('%'), default_value=40.0),
                     Float(title=_("Critical at"), unit=_('%'), default_value=50.0)
                 ])),
        ],
    ),
    TextAscii(
        title=_("Database Name"),
        help=_("Specify database names that the rule should apply to"),
    ),
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'azure_vms',
    _("Azure Virtual Machines"),
    Dictionary(
        help=_("To obtain the data required for this check, please configure"
               " the datasource program \"Agent Azure\"."),
        elements=[
            ('map_provisioning_states',
             Dictionary(
                 title=_("Map provisioning states"),
                 elements=[
                     ("succeeded", MonitoringState(title="succeeded")),
                     ("failed", MonitoringState(title="failed", default_value=2)),
                 ])),
            ('map_power_states',
             Dictionary(
                 title=_("Map power states"),
                 elements=[
                     ("starting", MonitoringState(title="starting")),
                     ("running", MonitoringState(title="running")),
                     ("stopping", MonitoringState(title="stopping", default_value=1)),
                     ("stopped", MonitoringState(title="stopped", default_value=1)),
                     ("deallocating", MonitoringState(title="deallocating")),
                     ("deallocated", MonitoringState(title="deallocated")),
                     ("unknown", MonitoringState(title=_("unknown"), default_value=3)),
                 ])),
        ],
    ),
    TextAscii(title=_("VM name")),
    match_type='dict',
)


def _azure_vms_summary_levels(title, lower=(None, None), upper=(None, None)):
    return Dictionary(
        title=_(title),
        elements=[
            ("levels_lower",
             Tuple(
                 title=_("Lower levels"),
                 elements=[
                     Integer(title=_("Warning below"), default_value=lower[0]),
                     Integer(title=_("Critical below"), default_value=lower[1]),
                 ])),
            ("levels",
             Tuple(
                 title=_("Upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), default_value=upper[0]),
                     Integer(title=_("Critical at"), default_value=upper[1]),
                 ])),
        ])


register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'azure_vms_summary',
    _("Azure Virtual Machines Summary"),
    Dictionary(
        help=_("To obtain the data required for this check, please configure"
               " the datasource program \"Agent Azure\"."),
        elements=[
            ('levels_provisioning',
             Dictionary(
                 title=_("Levels for provisioning count"),
                 elements=[
                     ("succeeded", _azure_vms_summary_levels("Succeeded provionings", (0, -1))),
                     ("failed", _azure_vms_summary_levels("Failed provisionings", (-1, -1),
                                                          (1, 1))),
                 ])),
            ('levels_power',
             Dictionary(
                 title=_("Levels for power state count"),
                 elements=[
                     ("starting", _azure_vms_summary_levels("Starting VMs")),
                     ("running", _azure_vms_summary_levels("Running VMs")),
                     ("stopping", _azure_vms_summary_levels("Stopping VMs")),
                     ("stopped", _azure_vms_summary_levels("Stopped VMs")),
                     ("deallocating", _azure_vms_summary_levels("Deallocating VMs")),
                     ("unknown", _azure_vms_summary_levels("VMs in unknown state", upper=(1, 1))),
                 ])),
        ],
    ),
    None,
    match_type='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    'azure_virtualnetworkgateways',
    _("Azure VNet Gateway"),
    Dictionary(elements=[
        (
            'connections_levels_upper',
            Tuple(
                title=_("Upper levels on number of Point-to-site connections"),
                elements=[Float(title=_("Warning at")),
                          Float(title=_("Critical at"))]),
        ),
        (
            'connections_levels_lower',
            Tuple(
                title=_("Lower levels on number of Point-to-site connections"),
                elements=[Float(title=_("Warning below")),
                          Float(title=_("Critical below"))]),
        ),
        (
            'p2s_bandwidth_levels_upper',
            Tuple(
                title=_("Upper levels on Point-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning at"), unit="B/s"),
                    Float(title=_("Critical at"), unit="B/s")
                ]),
        ),
        (
            'p2s_bandwidth_levels_lower',
            Tuple(
                title=_("Lower levels on Point-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning below"), unit="B/s"),
                    Float(title=_("Critical below"), unit="B/s")
                ]),
        ),
        (
            's2s_bandwidth_levels_upper',
            Tuple(
                title=_("Upper levels on Site-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning at"), unit="B/s"),
                    Float(title=_("Critical at"), unit="B/s")
                ]),
        ),
        (
            's2s_bandwidth_levels_lower',
            Tuple(
                title=_("Lower levels on Site-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning below"), unit="B/s"),
                    Float(title=_("Critical below"), unit="B/s")
                ]),
        ),
    ]),
    TextAscii(
        title=_("Virtual network gateway name"),
        help=_("Specify virtual network gateway names that the rule should apply to"),
    ),
    match_type='dict',
)
