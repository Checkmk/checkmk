#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
    FixedValue,
    Float,
    TextAscii,
    Tuple,
    ListChoice,
)
from cmk.gui.plugins.wato import (
    HostRulespec,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _vs_cisco_dom(which_levels):
    def _button_text_warn(which_levels):
        if which_levels == "upper":
            text = "Warning at"
        elif which_levels == "lower":
            text = "Warning below"
        else:
            raise ValueError
        return text

    def _button_text_crit(which_levels):
        if which_levels == "upper":
            text = "Critical at"
        elif which_levels == "lower":
            text = "Critical below"
        else:
            raise ValueError
        return text

    return (
        "power_levels_%s" % which_levels,
        Alternative(
            title="%s levels for the signal power" % which_levels.title(),
            style="dropdown",
            default_value=True,  # use device levels
            elements=[
                FixedValue(
                    True,
                    title=_("Use device levels"),
                    totext="",
                ),
                Tuple(title=_("Use the following levels"),
                      elements=[
                          Float(title=_(_button_text_warn(which_levels)), unit=_("dBm")),
                          Float(title=_(_button_text_crit(which_levels)), unit=_("dBm")),
                      ]),
                FixedValue(
                    False,
                    title=_("No levels"),
                    totext="",
                ),
            ]))


@rulespec_registry.register
class RulespecCheckgroupParametersCiscoDOM(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "cisco_dom"

    @property
    def title(self):
        return _("CISCO Digital Optical Monitoring (DOM)")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            (_vs_cisco_dom("upper")),
            (_vs_cisco_dom("lower")),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Sensor description if present, sensor index otherwise"))


@rulespec_registry.register
class RulespecDiscoveryCiscoDomRules(HostRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "discovery_cisco_dom_rules"

    @property
    def match_type(self):
        return "dict"

    @property
    def valuespec(self):
        return Dictionary(title=_("Cisco DOM Discovery"),
                          elements=[
                              ("admin_states",
                               ListChoice(
                                   title=_("Admin states to discover"),
                                   choices={
                                       1: _("up"),
                                       2: _("down"),
                                       3: _("testing"),
                                   },
                                   toggle_all=True,
                                   default_value=['1', '2', '3'],
                               )),
                          ])
