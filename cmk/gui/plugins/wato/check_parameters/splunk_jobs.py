#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_splunk_jobs():
    return Dictionary(
        optional_keys=True,
        elements=[
            (
                "job_count",
                Tuple(
                    title=_("Number of jobs"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "failed_count",
                Tuple(
                    title=_("Number of failed jobs"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "zombie_count",
                Tuple(
                    title=_("Number of zombie jobs"),
                    help=_(
                        "Splunk calls a search a zombie when the search is "
                        "no longer running, but did not declare explicitly that "
                        "it has finished its work."
                    ),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="splunk_jobs",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_splunk_jobs,
        title=lambda: _("Splunk Jobs"),
    )
)
