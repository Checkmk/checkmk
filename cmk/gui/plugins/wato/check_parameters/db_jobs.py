#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, DropdownChoice, MonitoringState, Tuple

run_duration = Tuple(
    title=_("Maximum run duration for last execution"),
    help=_("Here you can define an upper limit for the run duration of last execution of the job."),
    elements=[
        Age(title=_("warning at")),
        Age(title=_("critical at")),
    ],
)

ignore_db_status = DropdownChoice(
    title=_("Job State"),
    help=_("The state of the job is ignored by default."),
    choices=[
        (True, _("Ignore the state of the Job")),
        (False, _("Consider the state of the job")),
    ],
)

status_disabled_jobs = MonitoringState(
    title=_("Status of service in case of disabled job"),
    default_value=0,
)

status_missing_jobs = MonitoringState(
    title=_("Status of service in case of missing job"),
    default_value=2,
)

missinglog = MonitoringState(
    default_value=1,
    title=_("State in case of Job has no log information"),
    help=_(
        "It is possible that a job has no log information. This also means "
        "that the job has no last running state as this is obtained from the log. "
        "The last run state is ignored when no log information is found."
    ),
)
