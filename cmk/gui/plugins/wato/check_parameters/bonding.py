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
    MonitoringState,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersNetworking,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking, "bonding", _("Status of Linux bonding interfaces"),
    Dictionary(elements=[
        ("expect_active",
         DropdownChoice(
             title=_("Warn on unexpected active interface"),
             choices=[
                 ("ignore", _("ignore which one is active")),
                 ("primary", _("require primary interface to be active")),
                 ("lowest", _("require interface that sorts lowest alphabetically")),
             ],
             default_value="ignore",
         )),
        ("ieee_302_3ad_agg_id_missmatch_state",
         MonitoringState(
             title=_("State for missmatching Aggregator IDs for LACP"),
             default_state=1,
         )),
    ]), TextAscii(title=_("Name of the bonding interface"),), "dict")
