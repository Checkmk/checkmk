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
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_storcli_pdisks():
    return TextAscii(
        title=_("PDisk EID:Slot-Device"),
        allow_empty=False,
    )


def _parameter_valuespec_storcli_pdisks():
    return Dictionary(
        title=_("Evaluation of PDisk States"),
        elements=[
            ("Dedicated Hot Spare",
             MonitoringState(
                 title=_("State for <i>Dedicated Hot Spare</i>"),
                 default_value=0,
             )),
            ("Global Hot Spare",
             MonitoringState(
                 title=_("State for <i>Global Hot Spare</i>"),
                 default_value=0,
             )),
            ("Unconfigured Good",
             MonitoringState(
                 title=_("State for <i>Unconfigured Good</i>"),
                 default_value=0,
             )),
            ("Unconfigured Bad",
             MonitoringState(
                 title=_("State for <i>Unconfigured Bad</i>"),
                 default_value=1,
             )),
            ("Online", MonitoringState(
                title=_("State for <i>Online</i>"),
                default_value=0,
            )),
            ("Offline", MonitoringState(
                title=_("State for <i>Offline</i>"),
                default_value=2,
            )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="storcli_pdisks",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_storcli_pdisks,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_storcli_pdisks,
        title=lambda: _("LSI RAID physical disks (StorCLI)"),
    ))
