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
    Alternative,
    Dictionary,
    FixedValue,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_postgres_maintenance():
    return Dictionary(
        help=_("With this rule you can set limits for the VACUUM and ANALYZE operation of "
               "a PostgreSQL database. Keep in mind that each table within a database is checked "
               "with this limits."),
        elements=[
            ("last_vacuum",
             Tuple(
                 title=_("Time since the last VACUUM"),
                 elements=[
                     Age(title=_("Warning if older than"), default_value=86400 * 7),
                     Age(title=_("Critical if older than"), default_value=86400 * 14)
                 ],
             )),
            ("last_analyze",
             Tuple(
                 title=_("Time since the last ANALYZE"),
                 elements=[
                     Age(title=_("Warning if older than"), default_value=86400 * 7),
                     Age(title=_("Critical if older than"), default_value=86400 * 14)
                 ],
             )),
            ("never_analyze_vacuum",
             Alternative(
                 title=_("Never analyzed/vacuumed tables"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Age of never analyzed/vacuumed tables"),
                         elements=[
                             Age(title=_("Warning if older than"), default_value=0),
                             Age(title=_("Critical if older than"),
                                 default_value=1000 * 365 * 24 * 3600)
                         ],
                     ),
                     FixedValue(
                         None,
                         title=_("Do not check age of never analyzed/vacuumed tables"),
                         totext="",
                     ),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="postgres_maintenance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of the database"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_postgres_maintenance,
        title=lambda: _("PostgreSQL VACUUM and ANALYZE"),
    ))
