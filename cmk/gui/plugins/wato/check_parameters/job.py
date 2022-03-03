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
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DropdownChoice,
    Integer,
    ListOf,
    MonitoringState,
    TextInput,
    Tuple,
)


def _deprecation_message() -> str:
    return _('This option is deprecated. Please use the ruleset <i>"%s"</i> instead.') % _(
        "Aggregation options for clustered services"
    )


def _parameter_valuespec_job():
    return Dictionary(
        elements=[
            (
                "age",
                Tuple(
                    title=_("Maximum time since last start of job execution"),
                    elements=[
                        Age(title=_("Warning at"), default_value=0),
                        Age(title=_("Critical at"), default_value=0),
                    ],
                ),
            ),
            (
                "exit_code_to_state_map",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            Integer(title=_("Exit code")),
                            MonitoringState(
                                title=_("Resulting state"),
                            ),
                        ],
                        default_value=(0, 0),
                    ),
                    title=_("Explicit mapping of job exit codes to states"),
                    help=_(
                        "Here you can define a mapping between possible exit codes and service states. "
                        "If no mapping is defined, the check becomes CRITICAL when the exit code is not 0. "
                        "If an exit code occurs that is not defined in this mapping, the check becomes CRITICAL. "
                        "If you happen to define the same exit code multiple times the first entry will be used."
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "outcome_on_cluster",
                DropdownChoice(
                    title="%s - %s"
                    % (
                        _("Clusters: Preferred check result of local checks"),
                        _deprecation_message(),
                    ),
                    choices=[],
                    deprecated_choices=("worst", "best"),
                    invalid_choice_title=_('Old setting: "%s". Choose that in the new ruleset.'),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="job",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Job name"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_job,
        title=lambda: _("mk-job job age"),
    )
)
