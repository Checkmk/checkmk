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
from cmk.gui.valuespec import Age, Dictionary, Integer, MonitoringState, TextInput, Tuple


def _parameter_valuespec_jenkins_jobs():
    return Dictionary(
        elements=[
            (
                "jenkins_job_score",
                Tuple(
                    title=_("Job score"),
                    elements=[
                        Integer(title=_("Warning below"), unit="%"),
                        Integer(title=_("Critical below"), unit="%"),
                    ],
                ),
            ),
            (
                "jenkins_last_build",
                Tuple(
                    title=_("Time since last build"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "jenkins_time_since",
                Tuple(
                    title=_("Time since last successful build"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "jenkins_build_duration",
                Tuple(
                    title=_("Duration of last build"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "job_state",
                Dictionary(
                    title=_("Override check state based on job state"),
                    elements=[
                        (
                            "aborted",
                            MonitoringState(
                                title=_("State when job is in state aborted"), default_value=0
                            ),
                        ),
                        (
                            "blue",
                            MonitoringState(
                                title=_("State when job is in state success"), default_value=0
                            ),
                        ),
                        (
                            "disabled",
                            MonitoringState(
                                title=_("State when job is in state disabled"), default_value=0
                            ),
                        ),
                        (
                            "notbuilt",
                            MonitoringState(
                                title=_("State when job is in state not built"), default_value=0
                            ),
                        ),
                        (
                            "red",
                            MonitoringState(
                                title=_("State when job is in state failed"), default_value=2
                            ),
                        ),
                        (
                            "yellow",
                            MonitoringState(
                                title=_("State when job is in state unstable"), default_value=1
                            ),
                        ),
                    ],
                ),
            ),
            (
                "build_result",
                Dictionary(
                    title=_("Override check state based on last build result"),
                    elements=[
                        (
                            "success",
                            MonitoringState(
                                title=_("State when last build result is: success"), default_value=0
                            ),
                        ),
                        (
                            "unstable",
                            MonitoringState(
                                title=_("State when last build result is: unstable"),
                                default_value=1,
                            ),
                        ),
                        (
                            "failure",
                            MonitoringState(
                                title=_("State when last build result is: failed"), default_value=2
                            ),
                        ),
                        (
                            "aborted",
                            MonitoringState(
                                title=_("State when last build result is: aborted"), default_value=0
                            ),
                        ),
                        (
                            "null",
                            MonitoringState(
                                title=_("State when last build result is: module not built"),
                                default_value=1,
                            ),
                        ),
                        (
                            "none",
                            MonitoringState(
                                title=_("State when build result is: running"), default_value=0
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jenkins_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Job name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jenkins_jobs,
        title=lambda: _("Jenkins jobs"),
    )
)
