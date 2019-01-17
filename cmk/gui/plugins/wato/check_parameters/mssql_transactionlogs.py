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
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)
from cmk.gui.plugins.wato.check_parameters.mssql_datafiles import levels_absolute_or_dynamic

register_check_parameters(
    RulespecGroupCheckParametersApplications, "mssql_transactionlogs",
    _("MSSQL Transactionlog Sizes"),
    Dictionary(
        title=_("File Size Levels"),
        help=_("Specify levels for transactionlogs of a database. Please note that relative "
               "levels will only work if there is a max_size set for the file on the database "
               "side."),
        elements=[
            ("used_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("used"))),
            ("allocated_used_levels",
             levels_absolute_or_dynamic(_("Transactionlog"), _("used of allocation"))),
            ("allocated_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("allocated"))),
        ]), TextAscii(title=_("Database Name"), allow_empty=False), "dict")
