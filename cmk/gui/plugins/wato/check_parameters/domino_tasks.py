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
    FixedValue,
    Integer,
    RegExp,
    TextAscii,
    Transform,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "domino_tasks",
    _("Lotus Domino Tasks"),
    Dictionary(
        elements=[
            (
                "process",
                Alternative(
                    title=_("Name of the task"),
                    style="dropdown",
                    elements=[
                        TextAscii(
                            title=_("Exact name of the task"),
                            size=50,
                        ),
                        Transform(
                            RegExp(
                                size=50,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching tasks"),
                            help=_("This regex must match the <i>beginning</i> of the complete "
                                   "command line of the task including arguments"),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext="",
                            title=_("Match all tasks"),
                        )
                    ],
                    match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0))),
            ("warnmin",
             Integer(
                 title=_("Minimum number of matched tasks for WARNING state"),
                 default_value=1,
             )),
            ("okmin",
             Integer(
                 title=_("Minimum number of matched tasks for OK state"),
                 default_value=1,
             )),
            ("okmax",
             Integer(
                 title=_("Maximum number of matched tasks for OK state"),
                 default_value=99999,
             )),
            ("warnmax",
             Integer(
                 title=_("Maximum number of matched tasks for WARNING state"),
                 default_value=99999,
             )),
        ],
        required_keys=['warnmin', 'okmin', 'okmax', 'warnmax', 'process'],
    ),
    TextAscii(
        title=_("Name of service"),
        help=_("This name will be used in the description of the service"),
        allow_empty=False,
        regex="^[a-zA-Z_0-9 _.-]*$",
        regex_error=_("Please use only a-z, A-Z, 0-9, space, underscore, "
                      "dot and hyphen for your service description"),
    ),
    match_type="dict",
    has_inventory=False)
