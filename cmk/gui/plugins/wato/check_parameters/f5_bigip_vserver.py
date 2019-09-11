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
    TextAscii,
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    Levels,
)


def _parameter_valuespec_f5_bigip_vserver():
    return Dictionary(
        elements=[
            ("if_in_octets",
             Levels(
                 title=_("Incoming Traffic Maximum"),
                 unit=_("bytes/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_in_octets_lower",
             Levels(
                 title=_("Incoming Traffic Minimum"),
                 unit=_("bytes/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_out_octets",
             Levels(
                 title=_("Outgoing Traffic Maximum"),
                 unit=_("bytes/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_out_octets_lower",
             Levels(
                 title=_("Outgoing Traffic Minimum"),
                 unit=_("bytes/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_total_octets",
             Levels(
                 title=_("Total Traffic Maximum"),
                 unit=_("bytes/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_total_octets_lower",
             Levels(
                 title=_("Total Traffic Minimum"),
                 unit=_("bytes/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_in_pkts",
             Levels(
                 title=_("Incoming Packets Maximum"),
                 unit=_("packets/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_in_pkts_lower",
             Levels(
                 title=_("Incoming Packets Minimum"),
                 unit=_("packets/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_out_pkts",
             Levels(
                 title=_("Outgoing Packets Maximum"),
                 unit=_("packets/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_out_pkts_lower",
             Levels(
                 title=_("Outgoing Packets Minimum"),
                 unit=_("packets/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_total_pkts",
             Levels(
                 title=_("Total Packets Maximum"),
                 unit=_("packets/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            ("if_total_pkts_lower",
             Levels(
                 title=_("Total Packets Minimum"),
                 unit=_("packets/s"),
                 default_difference=(5, 8),
                 default_value=None,
             )),
            (
                "state",
                Dictionary(
                    title=_("Map states"),
                    elements=[
                        ("is_disabled", MonitoringState(title=_("Is disabled"), default_value=1)),
                        ("is_up_and_available",
                         MonitoringState(title=_("Is up and available"), default_value=0)),
                        ("is_currently_not_available",
                         MonitoringState(title=_("Is currently not available"), default_value=2)),
                        ("is_not_available",
                         MonitoringState(title=_("Is not available"), default_value=2)),
                        ("availability_is_unknown",
                         MonitoringState(title=_("Availability is unknown"), default_value=1)),
                        ("is_unlicensed", MonitoringState(title=_("Is unlicensed"),
                                                          default_value=3)),
                        (
                            "children_pool_members_down_if_not_available",
                            # Special handling, see check plugin
                            MonitoringState(title=_(
                                "The children pool member(s) are down if VServer is not available"),
                                            default_value=0)),
                    ],
                    optional_keys=False,
                )),
        ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="f5_bigip_vserver",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("VServer name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_bigip_vserver,
        title=lambda: _("F5 Loadbalancer VServer"),
    ))
