#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, Filesize, MonitoringState, TextInput, Tuple


def _parameter_valuespec_plesk_backups():
    return Dictionary(
        help=_("This check monitors backups configured for domains in plesk."),
        elements=[
            (
                "no_backup_configured_state",
                MonitoringState(title=_("State when no backup is configured"), default_value=1),
            ),
            (
                "no_backup_found_state",
                MonitoringState(title=_("State when no backup can be found"), default_value=1),
            ),
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
                    help=_(
                        "The maximum size of all files on the backup space. "
                        "This might be set to the allowed quotas on the configured "
                        "FTP server to be notified if the space limit is reached."
                    ),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
        ],
        optional_keys=["backup_age", "total_size"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="plesk_backups",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Service descriptions"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_plesk_backups,
        title=lambda: _("Plesk Backups"),
    )
)
