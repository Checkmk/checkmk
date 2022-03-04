#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput, Transform

rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="local",
        group=RulespecGroupEnforcedServicesApplications,
        item_spec=lambda: TextInput(title=_("Name of local item")),
        parameter_valuespec=lambda: Transform(
            valuespec=Dictionary(elements=[]), forth=lambda p: {}
        ),
        title=lambda: _("Local checks"),
    )
)

# We only need the above, there are no "true" parameters to this check plugin.


def _deprecation_message() -> str:
    return _('This ruleset is deprecated. Please use the ruleset <i>"%s"</i> instead.') % _(
        "Aggregation options for clustered services"
    )


def _parameter_valuespec_local():
    return Dictionary(
        elements=[
            (
                "outcome_on_cluster",
                DropdownChoice(
                    choices=[
                        ("worst", _("Worst state")),
                        ("best", _("Best state")),
                    ],
                    title="%s - %s %s"
                    % (
                        _("Clusters: Preferred check result of local checks"),
                        _deprecation_message(),
                        _("Old setting"),
                    ),
                    default_value="worst",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="local",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of local item")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_local,
        title=lambda: _("Local checks in Checkmk clusters") + " - " + _("Deprecated"),
        is_deprecated=True,
    )
)
