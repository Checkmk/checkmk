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
    ListChoice,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


@rulespec_registry.register
class RulespecCheckgroupParametersDocsisCmStatus(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "docsis_cm_status"

    @property
    def title(self):
        return _("Docsis Cable Modem Status")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("error_states",
             ListChoice(
                 title=_("Modem States that lead to a critical state"),
                 help=
                 _("If one of the selected states occurs the check will repsond with a critical state "
                  ),
                 choices=[
                     (1, "other"),
                     (2, "notReady"),
                     (3, "notSynchronized"),
                     (4, "phySynchronized"),
                     (5, "usParametersAcquired"),
                     (6, "rangingComplete"),
                     (7, "ipComplete"),
                     (8, "todEstablished"),
                     (9, "securityEstablished"),
                     (10, "paramTransferComplete"),
                     (11, "registrationComplete"),
                     (12, "operational"),
                     (13, "accessDenied"),
                 ],
                 default_value=[1, 2, 13],
             )),
            ("tx_power",
             Tuple(
                 title=_("Transmit Power"),
                 help=_("The operational transmit power"),
                 elements=[
                     Float(title=_("warning at"), unit="dBmV", default_value=20.0),
                     Float(title=_("critical at"), unit="dBmV", default_value=10.0),
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("ID of the Entry"))
