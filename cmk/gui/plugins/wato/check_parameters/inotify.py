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
    Age,
    Dictionary,
    DropdownChoice,
    ListOf,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


@rulespec_registry.register
class RulespecCheckgroupParametersInotify(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "inotify"

    @property
    def title(self):
        return _("INotify Levels")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_("This rule allows you to set levels for specific Inotify changes. "
                   "Keep in mind that you can only monitor operations which are actually "
                   "enabled in the Inotify plugin. So it might be a good idea to cross check "
                   "these levels here with the configuration rule in the agent bakery. "),
            elements=[
                ('age_last_operation',
                 ListOf(Tuple(elements=[
                     DropdownChoice(
                         title=_("INotify Operation"),
                         choices=[
                             ("create", _("Create")),
                             ("delete", _("Delete")),
                             ("open", _("Open")),
                             ("modify", _("Modify")),
                             ("access", _("Access")),
                             ("movedfrom", _("Moved from")),
                             ("movedto", _("Moved to")),
                             ("moveself", _("Move self")),
                         ],
                     ),
                     Age(title=_("Warning at")),
                     Age(title=_("Critical at")),
                 ],),
                        title=_("Age of last operation"),
                        movable=False)),
            ],
            optional_keys=None,
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("The filesystem path, prefixed with <i>File </i> or <i>Folder </i>"),)
