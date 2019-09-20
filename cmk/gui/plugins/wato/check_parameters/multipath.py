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
    Checkbox,
    Dictionary,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
    HostRulespec,
)


def _valuespec_inventory_multipath_rules():
    return Dictionary(
        title=_("Linux Multipath Inventory"),
        elements=[
            ("use_alias",
             Checkbox(
                 title=_("Use the multipath alias as service name, if one is set"),
                 label=_("use alias"),
                 help=_(
                     "If a multipath device has an alias then you can use it for specifying "
                     "the device instead of the UUID. The alias will then be part of the service "
                     "description. The UUID will be displayed in the plugin output."))),
        ],
        help=_(
            "This rule controls whether the UUID or the alias is used in the service description during "
            "discovery of Multipath devices on Linux."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        name="inventory_multipath_rules",
        valuespec=_valuespec_inventory_multipath_rules,
    ))


def _item_spec_multipath():
    return TextAscii(title=_("Name of the MP LUN"),
                     help=_("For Linux multipathing this is either the UUID (e.g. "
                            "60a9800043346937686f456f59386741), or the configured "
                            "alias."))


def _parameter_valuespec_multipath():
    return Alternative(
        help=_("This rules sets the expected number of active paths for a multipath LUN "
               "on Linux and Solaris hosts"),
        title=_("Expected number of active paths"),
        elements=[
            Integer(title=_("Expected number of active paths")),
            Tuple(
                title=_("Expected percentage of active paths"),
                elements=[
                    Percentage(title=_("Warning if less then")),
                    Percentage(title=_("Critical if less then")),
                ],
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="multipath",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_multipath,
        parameter_valuespec=_parameter_valuespec_multipath,
        title=lambda: _("Linux and Solaris Multipath Count"),
    ))
