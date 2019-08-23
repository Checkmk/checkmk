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
    DropdownChoice,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    ABCHostValueRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
)


@rulespec_registry.register
class RulespecEwonDiscoveryRules(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "ewon_discovery_rules"

    @property
    def valuespec(self):
        return DropdownChoice(
            title=_("eWON Discovery"),
            help=_("The ewon vpn routers can rely data from a secondary device via snmp. "
                   "It doesn't however allow discovery of the device type relayed this way. "
                   "To allow interpretation of the data you need to pick the device manually."),
            label=_("Select device type"),
            choices=[
                (None, _("None selected")),
                ("oxyreduct", _("Wagner OxyReduct")),
            ],
            default_value=None,
        )


@rulespec_registry.register
class RulespecCheckgroupParametersEwon(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "ewon"

    @property
    def title(self):
        return _("eWON SNMP Proxy")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            title=_("Device Type"),
            help=_("The eWON router can act as a proxy to metrics from a secondary non-snmp device."
                   "Here you can make settings to the monitoring of the proxied device."),
            elements=[("oxyreduct",
                       Dictionary(
                           title=_("Wagner OxyReduct"),
                           elements=[("o2_levels",
                                      Tuple(
                                          title=_("O2 levels"),
                                          elements=[
                                              Percentage(title=_("Warning at"), default_value=16.0),
                                              Percentage(title=_("Critical at"),
                                                         default_value=17.0),
                                              Percentage(title=_("Warning below"),
                                                         default_value=14.0),
                                              Percentage(title=_("Critical below"),
                                                         default_value=13.0),
                                          ],
                                      ))],
                       ))],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Item name"),
                         help=_("The item name. The meaning of this depends on the proxied device: "
                                "- Wagner OxyReduct: Name of the room/protection zone"))
