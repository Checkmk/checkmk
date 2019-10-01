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
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    Levels,
)


def _parameter_valuespec_f5_bigip_snat():
    return Dictionary(elements=[("if_in_octets",
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
                                 ))],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="f5_bigip_snat",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Source NAT Name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_bigip_snat,
        title=lambda: _("F5 Loadbalancer Source NAT"),
    ))
