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
    Float,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_postgres_stat_database():
    return Dictionary(
        help=_(
            "This check monitors how often database objects in a PostgreSQL Database are accessed"),
        elements=[
            (
                "blocks_read",
                Tuple(
                    title=_("Blocks read"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("blocks/s")),
                        Float(title=_("Critical at"), unit=_("blocks/s")),
                    ],
                ),
            ),
            (
                "xact_commit",
                Tuple(
                    title=_("Commits"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_fetched",
                Tuple(
                    title=_("Fetches"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_deleted",
                Tuple(
                    title=_("Deletes"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_updated",
                Tuple(
                    title=_("Updates"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_inserted",
                Tuple(
                    title=_("Inserts"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="postgres_stat_database",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Database name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_postgres_stat_database,
        title=lambda: _("PostgreSQL Database Statistics"),
    ))
