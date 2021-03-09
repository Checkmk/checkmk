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
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_db_bloat():
    return Dictionary(
        help=_("This rule allows you to configure bloat levels for a databases tablespace and "
               "indexspace."),
        elements=[
            ("table_bloat_abs",
             Tuple(
                 title=_("Table absolute bloat levels"),
                 elements=[
                     Filesize(title=_("Warning at")),
                     Filesize(title=_("Critical at")),
                 ],
             )),
            ("table_bloat_perc",
             Tuple(
                 title=_("Table percentage bloat levels"),
                 help=_("Percentage in respect to the optimal utilization. "
                        "For example if an alarm should raise at 50% wasted space, you need "
                        "to configure 150%"),
                 elements=[
                     Percentage(title=_("Warning at"), maxvalue=None),
                     Percentage(title=_("Critical at"), maxvalue=None),
                 ],
             )),
            ("index_bloat_abs",
             Tuple(
                 title=_("Index absolute levels"),
                 elements=[
                     Filesize(title=_("Warning at")),
                     Filesize(title=_("Critical at")),
                 ],
             )),
            ("index_bloat_perc",
             Tuple(
                 title=_("Index percentage bloat levels"),
                 help=_("Percentage in respect to the optimal utilization. "
                        "For example if an alarm should raise at 50% wasted space, you need "
                        "to configure 150%"),
                 elements=[
                     Percentage(title=_("Warning at"), maxvalue=None),
                     Percentage(title=_("Critical at"), maxvalue=None),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db_bloat",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of the database"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db_bloat,
        title=lambda: _("Database Bloat (PostgreSQL)"),
    ))
