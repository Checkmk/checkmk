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
    Integer,
    ListOf,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def levels_absolute_or_dynamic(name, value):
    return Alternative(
        title=_("Levels of %s %s") % (name, value),
        default_value=(80.0, 90.0),
        elements=[
            Tuple(title=_("Percentage %s space") % value,
                  elements=[
                      Percentage(title=_("Warning at"), unit=_("% used")),
                      Percentage(title=_("Critical at"), unit=_("% used")),
                  ]),
            Tuple(title=_("Absolute %s space") % value,
                  elements=[
                      Integer(title=_("Warning at"), unit=_("MB"), default_value=500),
                      Integer(title=_("Critical at"), unit=_("MB"), default_value=1000),
                  ]),
            ListOf(
                Tuple(
                    orientation="horizontal",
                    elements=[
                        Filesize(title=_(" larger than")),
                        Alternative(title=_("Levels for the %s %s size") % (name, value),
                                    elements=[
                                        Tuple(title=_("Percentage %s space") % value,
                                              elements=[
                                                  Percentage(title=_("Warning at"),
                                                             unit=_("% used")),
                                                  Percentage(title=_("Critical at"),
                                                             unit=_("% used")),
                                              ]),
                                        Tuple(title=_("Absolute free space"),
                                              elements=[
                                                  Integer(title=_("Warning at"), unit=_("MB")),
                                                  Integer(title=_("Critical at"), unit=_("MB")),
                                              ]),
                                    ]),
                    ],
                ),
                title=_('Dynamic levels'),
            ),
        ])


def _parameter_valuespec_mssql_datafiles():
    return Dictionary(
        title=_("File Size Levels"),
        help=_("Specify levels for datafiles of a database. Please note that relative "
               "levels will only work if there is a max_size set for the file on the database "
               "side."),
        elements=[
            ("used_levels", levels_absolute_or_dynamic(_("Datafile"), _("used"))),
            ("allocated_used_levels",
             levels_absolute_or_dynamic(_("Datafile"), _("used of allocation"))),
            ("allocated_levels", levels_absolute_or_dynamic(_("Datafile"), _("allocated"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_datafiles",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Database Name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_datafiles,
        title=lambda: _("MSSQL Datafile Sizes"),
    ))
