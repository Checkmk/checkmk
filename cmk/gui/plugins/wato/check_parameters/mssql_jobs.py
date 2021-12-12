#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.db_jobs import (
    ignore_db_status,
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


def _item_spec_mssql_jobs():
    return TextInput(
        title=_("Job Name"),
        help=_(
            "You can set explicit jobs by defining their job names. The job names can be found "
            'in the column "name" in the table "dbo.sysjobs" on the MSDB database.'
        ),
        allow_empty=False,
    )


def _parameter_valuespec_mssql_jobs():
    return Dictionary(
        help=_("A scheduled job on Microsoft SQL Server."),
        elements=[
            ("run_duration", run_duration),
            ("ignore_db_status", ignore_db_status),
            ("status_disabled_jobs", status_disabled_jobs),
            ("status_missing_jobs", status_missing_jobs),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mssql_jobs,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_jobs,
        title=lambda: _("MSSQL Jobs"),
    )
)
