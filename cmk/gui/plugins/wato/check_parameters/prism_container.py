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
    Alternative,
    Dictionary,
    Filesize,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_prism_container():
    return TextAscii(
        title=_("Container Name"),
        help=_("Name of the container"),
    )


def _parameter_valuespec_prism_container():
    return Dictionary(
        elements=[("levels",
                   Alternative(
                       title=_("Usage levels"),
                       default_value=(80.0, 90.0),
                       elements=[
                           Tuple(
                               title=_("Specify levels in percentage of total space"),
                               elements=[
                                   Percentage(title=_("Warning at"), unit=_("%")),
                                   Percentage(title=_("Critical at"), unit=_("%"))
                               ],
                           ),
                           Tuple(
                               title=_("Specify levels in absolute usage"),
                               elements=[
                                   Filesize(title=_("Warning at"),
                                            default_value=1000 * 1024 * 1024),
                                   Filesize(title=_("Critical at"),
                                            default_value=5000 * 1024 * 1024)
                               ],
                           ),
                       ],
                   ))],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_container",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_prism_container,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_container,
        title=lambda: _("Nutanix Prism"),
    ))
