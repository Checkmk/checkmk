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
    DropdownChoice,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def _item_spec_plugs():
    return TextAscii(
        title=_("Plug item number or name"),
        help=
        _("Whether you need the number or the name depends on the check. Just take a look to the service description."
         ),
        allow_empty=True)


def _parameter_valuespec_plugs():
    return DropdownChoice(help=_("This rule sets the required state of a PDU plug. It is meant to "
                                 "be independent of the hardware manufacturer."),
                          title=_("Required plug state"),
                          choices=[
                              ("on", _("Plug is ON")),
                              ("off", _("Plug is OFF")),
                          ],
                          default_value="on")


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="plugs",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_plugs,
        parameter_valuespec=_parameter_valuespec_plugs,
        title=lambda: _("State of PDU Plugs"),
    ))
