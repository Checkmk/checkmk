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
    Filesize,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_plesk_backups():
    return Dictionary(
        help=_("This check monitors backups configured for domains in plesk."),
        elements=[
            ("no_backup_configured_state",
             MonitoringState(title=_("State when no backup is configured"), default_value=1)),
            ("no_backup_found_state",
             MonitoringState(title=_("State when no backup can be found"), default_value=1)),
            (
                "backup_age",
                Tuple(
                    title=_("Maximum age of backups"),
                    help=_("The maximum age of the last backup."),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "total_size",
                Tuple(
                    title=_("Maximum size of all files on backup space"),
                    help=_("The maximum size of all files on the backup space. "
                           "This might be set to the allowed quotas on the configured "
                           "FTP server to be notified if the space limit is reached."),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
        ],
        optional_keys=['backup_age', 'total_size'],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="plesk_backups",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Service descriptions"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_plesk_backups,
        title=lambda: _("Plesk Backups"),
    ))
