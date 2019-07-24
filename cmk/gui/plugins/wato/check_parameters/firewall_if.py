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
    Integer,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    Levels,
)


@rulespec_registry.register
class RulespecCheckgroupParametersFirewallIf(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "firewall_if"

    @property
    def title(self):
        return _("Firewall Interfaces")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            (
                "ipv4_in_blocked",
                Levels(
                    title=_("Levels for rate of incoming IPv4 packets blocked"),
                    unit=_("pkts/s"),
                    default_levels=(100.0, 10000.0),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            ("average",
             Integer(
                 title=_("Averaging"),
                 help=_("When this option is activated then the block rate is being "
                        "averaged <b>before</b> the levels are being applied."),
                 unit=_("minutes"),
                 default_value=3,
                 minvalue=1,
                 label=_("Compute average over last "),
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Interface"),
            help=_("The description of the interface as provided by the device"),
        )
