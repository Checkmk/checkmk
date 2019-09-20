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
    Filesize,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_mongodb_mem():
    return Dictionary(
        title=_("MongoDB Memory"),
        elements=[
            ("resident_levels",
             Tuple(
                 title=_("Resident memory usage"),
                 help=
                 _("The value of resident is roughly equivalent to the amount of RAM, "
                   "currently used by the database process. In normal use this value tends to grow. "
                   "In dedicated database servers this number tends to approach the total amount of system memory."
                  ),
                 elements=[
                     Filesize(title=_("Warning at"), default_value=1 * 1024**3),
                     Filesize(title=_("Critical at"), default_value=2 * 1024**3),
                 ],
             )),
            ("mapped_levels",
             Tuple(
                 title=_("Mapped memory usage"),
                 help=_(
                     "The value of mapped shows the amount of mapped memory by the database. "
                     "Because MongoDB uses memory-mapped files, this value is likely to be to be "
                     "roughly equivalent to the total size of your database or databases."),
                 elements=[
                     Filesize(title=_("Warning at"), default_value=1 * 1024**3),
                     Filesize(title=_("Critical at"), default_value=2 * 1024**3),
                 ],
             )),
            ("virtual_levels",
             Tuple(
                 title=_("Virtual memory usage"),
                 help=_(
                     "Virtual displays the quantity of virtual memory used by the mongod process. "
                 ),
                 elements=[
                     Filesize(title=_("Warning at"), default_value=2 * 1024**3),
                     Filesize(title=_("Critical at"), default_value=4 * 1024**3),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mongodb_mem",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_mem,
        title=lambda: _("MongoDB Memory"),
    ))
