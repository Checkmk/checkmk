#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DropdownChoice,
    TextAscii,
    Tuple,
    ListOf,
    Integer,
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_job():
    return Dictionary(elements=[
        ("age",
         Tuple(
             title=_("Maximum time since last start of job execution"),
             elements=[
                 Age(title=_("Warning at"), default_value=0),
                 Age(title=_("Critical at"), default_value=0)
             ],
         )),
        ("exit_code_to_state_map",
         ListOf(
             Tuple(orientation="horizontal",
                   elements=[
                       Integer(title=_("Exit code")),
                       MonitoringState(title=_("Resulting state"),),
                   ],
                   default_value=(0, 0)),
             title=_("Explicit mapping of job exit codes to states"),
             help=
             _("Here you can define a mapping between possible exit codes and service states. "
               "If no mapping is defined, the check becomes CRITICAL when the exit code is not 0. "
               "If an exit code occurs that is not defined in this mapping, the check becomes CRITICAL. "
               "If you happen to define the same exit code multiple times the first entry will be used."
              ),
             allow_empty=False,
         )),
        ("outcome_on_cluster",
         DropdownChoice(
             title=_("Clusters: Prefered check result of local checks"),
             help=_("If you're running local checks on clusters via clustered services rule "
                    "you can influence the check result with this rule. You can choose between "
                    "best or worst state. Default setting is worst state."),
             choices=[
                 ("worst", _("Worst state")),
                 ("best", _("Best state")),
             ],
             default_value="worst")),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="job",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Job name"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_job,
        title=lambda: _("mk-job job age"),
    ))
