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
    Checkbox,
    Dictionary,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    HostRulespec,
)
from cmk.gui.plugins.wato.check_parameters.mssql_datafiles import levels_absolute_or_dynamic
from cmk.gui.plugins.wato.check_parameters.utils import mssql_item_spec_instance_database_file


def _valuespec_mssql_transactionlogs_discovery():
    return Dictionary(title=_("MSSQL Datafile and Transactionlog Discovery"),
                      elements=[
                          ("summarize_datafiles",
                           Checkbox(
                               title=_("Display only a summary of all Datafiles"),
                               label=_("Summarize Datafiles"),
                           )),
                          ("summarize_transactionlogs",
                           Checkbox(
                               title=_("Display only a summary of all Transactionlogs"),
                               label=_("Summarize Transactionlogs"),
                           )),
                      ],
                      optional_keys=[])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="mssql_transactionlogs_discovery",
        valuespec=_valuespec_mssql_transactionlogs_discovery,
    ))


def _parameter_valuespec_mssql_transactionlogs():
    return Dictionary(
        title=_("File Size Levels"),
        help=_("Specify levels for transactionlogs of a database. Please note that relative "
               "levels will only work if there is a max_size set for the file on the database "
               "side."),
        elements=[
            ("used_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("used"))),
            ("allocated_used_levels",
             levels_absolute_or_dynamic(_("Transactionlog"), _("used of allocation"))),
            ("allocated_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("allocated"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_transactionlogs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_database_file,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_transactionlogs,
        title=lambda: _("MSSQL Transactionlog Sizes"),
    ))
