#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, CascadingDropdown, Dictionary, Tuple


def __levels(title):
    return CascadingDropdown(
        title=title,
        choices=[
            ("no_levels", _("No levels"), None),
            (
                "levels",
                _("Impose levels"),
                Tuple(elements=[Age(title=_("Warning above")), Age(title=_("Critical above"))]),
            ),
        ],
        default_value="no_levels",
    )


def _parameter_valuespec():
    return Dictionary(
        help=_(
            (
                "A Deployment enters various states during its lifecycle. Depending on this a "
                "Deployment may present different conditions. You can set a time for how long "
                "a condition is allowed to be in a certain state before the check alerts."
            )
        ),
        elements=[
            ("progressing", __levels(_("Time until alert, if deployment not in progressing"))),
            ("available", __levels(_("Time until alert, if deployment not available"))),
            ("replicafailure", __levels(_("Time until alert, if deployment in replica failure"))),
        ],
        optional_keys=["progressing", "available", "replicafailure"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_deployment_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes deployment conditions"),
    )
)
