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
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersOracleRecoveryStatus(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "oracle_recovery_status"

    @property
    def title(self):
        return _("Oracle Recovery Status")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("levels",
             Tuple(
                 title=_("Levels for checkpoint time"),
                 elements=[
                     Age(title=_("warning if higher then"), default_value=1800),
                     Age(title=_("critical if higher then"), default_value=3600),
                 ],
             )),
            ("backup_age",
             Tuple(
                 title=_("Levels for user managed backup files"),
                 help=_("Important! This checks is only for monitoring of datafiles "
                        "who were left in backup mode. "
                        "(alter database datafile ... begin backup;) "),
                 elements=[
                     Age(title=_("warning if higher then"), default_value=1800),
                     Age(title=_("critical if higher then"), default_value=3600),
                 ],
             ))
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Database SID"), size=12, allow_empty=False)
