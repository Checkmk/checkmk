#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.db_jobs import (
    get_consider_job_status_valuespec,
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
from cmk.gui.valuespec import Dictionary, Migrate, TextInput


def _item_spec_oracle_jobs():
    return TextInput(
        title=_("Scheduler job name"),
        help=_(
            "Here you can set explicit scheduler jobs by defining them via SID, job owner "
            "and job name, separated by a dot, for example <tt>TUX12C.SYS.PURGE_LOG</tt>"
        ),
        regex=r".+\..+",
        allow_empty=False,
    )


# the migration is introduced in 2.2.0i1
def migrate_disabled(v: dict[str, object]) -> dict[str, object]:
    if (disabled := v.pop("disabled", None)) is not None:
        v["consider_job_status"] = "ignore" if disabled else "consider"

    return v


def _parameter_valuespec_oracle_jobs() -> Migrate:
    return Migrate(
        Dictionary(
            help=_(
                "A scheduler job is an object in an Oracle database which could be "
                "compared to a cron job on unix."
            ),
            elements=[
                ("run_duration", run_duration),
                ("consider_job_status", get_consider_job_status_valuespec()),
                ("status_disabled_jobs", status_disabled_jobs),
                ("status_missing_jobs", status_missing_jobs),
                ("missinglog", missinglog),
            ],
        ),
        migrate=migrate_disabled,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_oracle_jobs,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_jobs,
        title=lambda: _("Oracle scheduler job"),
    )
)
