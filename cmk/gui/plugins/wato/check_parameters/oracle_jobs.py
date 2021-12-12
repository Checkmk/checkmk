#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.db_jobs import (
    ignore_db_status,
    missinglog,
    run_duration,
    status_disabled_jobs,
    status_missing_jobs,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _item_spec_oracle_jobs():
    return TextInput(
        title=_("Scheduler Job Name"),
        help=_(
            "Here you can set explicit Scheduler-Jobs by defining them via SID, Job-Owner "
            "and Job-Name, separated by a dot, for example <tt>TUX12C.SYS.PURGE_LOG</tt>"
        ),
        regex=r".+\..+",
        allow_empty=False,
    )


def _parameter_valuespec_oracle_jobs():
    return Dictionary(
        help=_(
            "A scheduler job is an object in an ORACLE database which could be "
            "compared to a cron job on Unix. "
        ),
        elements=[
            ("run_duration", run_duration),
            ("disabled", ignore_db_status),
            ("status_disabled_jobs", status_disabled_jobs),
            ("status_missing_jobs", status_missing_jobs),
            ("missinglog", missinglog),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_oracle_jobs,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_jobs,
        title=lambda: _("Oracle Scheduler Job"),
    )
)
