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
    DropdownChoice,
    ListOf,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.check_parameters.db2_tablespaces import db_levels_common


def _item_spec_oracle_tablespaces():
    return TextAscii(
        title=_("Explicit tablespaces"),
        help=
        _("Here you can set explicit tablespaces by defining them via SID and the tablespace name, separated by a dot, for example <b>pengt.TEMP</b>"
         ),
        regex=r'.+\..+',
        allow_empty=False)


def _parameter_valuespec_oracle_tablespaces():
    return Dictionary(
        help=_("A tablespace is a container for segments (tables, indexes, etc). A "
               "database consists of one or more tablespaces, each made up of one or "
               "more data files. Tables and indexes are created within a particular "
               "tablespace. "
               "This rule allows you to define checks on the size of tablespaces."),
        elements=db_levels_common() + [
            ("autoextend",
             DropdownChoice(
                 title=_("Expected autoextend setting"),
                 choices=[
                     (True, _("Autoextend is expected to be ON")),
                     (False, _("Autoextend is expected to be OFF")),
                     (None, _("Autoextend will be ignored")),
                 ],
             )),
            ("autoextend_severity",
             MonitoringState(
                 title=_("Severity of invalid autoextend setting"),
                 default_value=2,
             )),
            ("defaultincrement",
             DropdownChoice(
                 title=_("Default Increment"),
                 choices=[
                     (True, _("State is WARNING in case the next extent has the default size.")),
                     (False, _("Ignore default increment")),
                 ],
             )),
            ("map_file_online_states",
             ListOf(
                 Tuple(
                     orientation="horizontal",
                     elements=[
                         DropdownChoice(choices=[
                             ("RECOVER", _("Recover")),
                             ("OFFLINE", _("Offline")),
                         ],),
                         MonitoringState()
                     ],
                 ),
                 title=_('Map file online states'),
             )),
            ("temptablespace",
             DropdownChoice(
                 title=_("Monitor temporary Tablespace"),
                 choices=[
                     (False, _("Ignore temporary Tablespaces (Default)")),
                     (True, _("Apply rule to temporary Tablespaces")),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_tablespaces",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_oracle_tablespaces,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_tablespaces,
        title=lambda: _("Oracle Tablespaces"),
    ))
