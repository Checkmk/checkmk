#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.db_jobs import (
    get_consider_job_status_valuespec,
    get_default_consider_job_status_choices,
    run_duration,
    status_disabled_jobs,
    status_missing_jobs,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Migrate, TextInput


def _item_spec_mssql_jobs():
    return TextInput(
        title=_("Job ID"),
        help=_(
            "You can set explicit jobs by defining their IDs. "
            "The job ID is a combination of the job name and the name of the instance the job runs on: `{job_name} - {instance_name}`. "
            'The job names can be found in the column "name" in the table "dbo.sysjobs" on the MSDB database.'
        ),
        allow_empty=False,
    )


def get_consider_job_status_choices() -> tuple[tuple[str, str], tuple[str, str], tuple[str, str]]:
    return get_default_consider_job_status_choices() + (
        ("consider_if_enabled", _("Consider the state of the job only if the job is enabled")),
    )


# the migration is introduced in 2.2.0i1
def migrate_ignore_db_status(v: dict[str, object]) -> dict[str, object]:
    if (ignore_status := v.pop("ignore_db_status", None)) is not None:
        v["consider_job_status"] = "ignore" if ignore_status else "consider"

    return v


def _parameter_valuespec_mssql_jobs() -> Migrate:
    choices = get_consider_job_status_choices()
    return Migrate(
        Dictionary(
            help=_("A scheduled job on Microsoft SQL Server."),
            elements=[
                ("run_duration", run_duration),
                ("consider_job_status", get_consider_job_status_valuespec(choices)),
                ("status_disabled_jobs", status_disabled_jobs),
                ("status_missing_jobs", status_missing_jobs),
            ],
        ),
        migrate=migrate_ignore_db_status,
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
