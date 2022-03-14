#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import age_levels_dropdown
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, ListOf, RegExp, Tuple

DESIRED_PHASE = [
    "Running",
    "Succeeded",
]


def __element():
    return Tuple(
        elements=[
            age_levels_dropdown(),
            ListOf(
                valuespec=RegExp(
                    mode=RegExp.infix,
                    title=_("Status"),
                    allow_empty=False,
                    size=50,
                ),
                add_label=_("Add new status"),
                allow_empty=False,
                movable=False,
                help=RegExp(mode=RegExp.infix).help(),
            ),
        ],
    )


def _parameter_valuespec_kube_pod_status():
    return Dictionary(
        title=_("Interpretation of pod status"),
        help=_(
            "You can configure groups of statuses and the time after which a warn/crit result is "
            "returned. The first matching group is selected, each entry within a group is a "
            "regular expression. The service tracks how long a Pod is part of a group, rather than "
            "the duration of an individual status. This means the counter will only be reset when "
            "changing groups. Note, that if you change any group of statuses, the timer will be "
            "reset. Changing levels has no effect on timers."
        ),
        elements=[
            (
                "groups",
                ListOf(
                    valuespec=__element(),
                    title=_("Groups"),
                    default_value=[
                        (
                            "no_levels",
                            DESIRED_PHASE,
                        ),
                        (
                            ("levels", (300, 600)),
                            [".*"],
                        ),
                    ],
                    add_label=_("Add new group"),
                ),
            ),
        ],
        optional_keys=False,
        indent=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_pod_status",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_kube_pod_status,
        title=lambda: _("Kubernetes pod status"),
    )
)
