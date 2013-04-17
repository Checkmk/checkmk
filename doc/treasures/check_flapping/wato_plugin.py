#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# This is the WATO plugin to configure the active check check_flapping
# via WATO. This plugin must be placed in web/plugins/wato directory.

register_rule("activechecks",
    "active_checks:flapping",
    Tuple(
        title = _("Check Flapping Services"),
        help = _("Checks wether or not one or several services changed their states "
                 "too often in the given timeperiod."),
        elements = [
            TextUnicode(
                title = _("Name"),
                help = _("Will be used in the service description"),
                allow_empty = False
            ),
            ListOfStrings(
                title = _("Patterns to match services"),
                orientation = "horizontal",
                valuespec = RegExp(size = 30),
            ),
            Dictionary(
                title = _("Optional parameters"),
                elements = [
                    ("num_state_changes",
                        Tuple(
                            title = _("State change thresholds"),
                            elements = [
                                Integer(
                                    title = _("Warning at"),
                                    default_value = 2
                                ),
                                Integer(
                                    title = _("Critical at"),
                                    default_value = 3
                                ),
                            ]
                        )
                    ),
                    ("timerange",
                        Integer(
                            title = _("Timerange to check"),
                            unit = _('Minutes'),
                            default_value = 60
                        ),
                    )
                ]
            )
        ]
    ),
    match = 'all')

