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
    Checkbox,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersNetworking,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


@rulespec_registry.register
class RulespecCheckgroupParametersBrocadeOptical(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "brocade_optical"

    @property
    def title(self):
        return _("Brocade Optical Signal")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                ('temp', Checkbox(title=_("Temperature Alert"), default_value=True)),
                ('tx_light',
                 Checkbox(title=_("TX Light alert"), label=_("TX Light alert"),
                          default_value=False)),
                ('rx_light',
                 Checkbox(title=_("RX Light alert"), label=_("TX Light alert"),
                          default_value=False)),
                ('lanes',
                 Checkbox(title=_("Lanes"),
                          label=_("Monitor & Graph Lanes"),
                          help=_("Monitor and graph the lanes, if the port has multiple"))),
            ],
            optional_keys=[],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Interface id"))
