#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary, ListOf, MonitoringState, RegExp


def _parameter_valuespec_systemd_units_summary() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "states",
                Dictionary(
                    title=_("Map systemd states to monitoring states"),
                    elements=[
                        (
                            "active",
                            MonitoringState(
                                title=_("Monitoring state if unit is active"),
                                default_value=0,
                            ),
                        ),
                        (
                            "inactive",
                            MonitoringState(
                                title=_("Monitoring state if unit is inactive"),
                                default_value=0,
                            ),
                        ),
                        (
                            "failed",
                            MonitoringState(
                                title=_("Monitoring state if unit is failed"),
                                default_value=2,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "states_default",
                MonitoringState(
                    title=_("Monitoring state for any other unit state"),
                    default_value=2,
                ),
            ),
            (
                "ignored",
                ListOf(
                    valuespec=RegExp(
                        title=_("Pattern (Regex)"),
                        size=40,
                        mode=RegExp.infix,
                    ),
                    title=_("Exclude units matching provided regex patterns"),
                    help=_(
                        "You can optionally define one or multiple regular expressions."
                        " Matching units are excluded."
                        " This allows to ignore services which are known to fail beforehand."
                    ),
                    add_label=_("Add pattern"),
                ),
            ),
            (
                "activating_levels",
                SimpleLevels(
                    Age,
                    title=_("Tolerance period for 'activating' state"),
                    help=_(
                        "Choose time levels for which a unit is allowed to be in an 'activating' state"
                    ),
                    default_levels=(30, 60),
                ),
            ),
            (
                "deactivating_levels",
                SimpleLevels(
                    Age,
                    title=_("Tolerance period for 'deactivating' state"),
                    help=_(
                        "Choose time levels (in seconds) for which a unti is allowed to be in an 'deactivating' state"
                    ),
                    default_value=(30, 60),
                ),
            ),
            (
                "reloading_levels",
                SimpleLevels(
                    Age,
                    title=_("Tolerance period for 'reloading' state"),
                    help=_(
                        "Choose time levels (in seconds) for which a unit is allowed to be in a 'reloading' state"
                    ),
                    default_value=(30, 60),
                ),
            ),
        ],
        help=_(
            "This ruleset only applies to the summary Systemd service and not the individual one."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="systemd_services_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_units_summary,
        title=lambda: _("Systemd services summary"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="systemd_sockets_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_units_summary,
        title=lambda: _("Systemd sockets summary"),
    )
)
