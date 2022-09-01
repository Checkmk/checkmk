#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

from .systemd_services import SERVICE, SOCKET, UnitNames


def _parameter_valuespec_systemd_units_summary(unit: UnitNames) -> Dictionary:
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
                                title=_("Monitoring state if %s is active") % unit.singular,
                                default_value=0,
                            ),
                        ),
                        (
                            "inactive",
                            MonitoringState(
                                title=_("Monitoring state if %s is inactive") % unit.singular,
                                default_value=0,
                            ),
                        ),
                        (
                            "failed",
                            MonitoringState(
                                title=_("Monitoring state if %s is failed") % unit.singular,
                                default_value=2,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "states_default",
                MonitoringState(
                    title=_("Monitoring state for any other %s state") % unit.singular,
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
                    title=_("Exclude %s matching provided regex patterns") % unit.plural,
                    help=_(
                        "<p>You can optionally define one or multiple regular expressions "
                        "where a matching case will result in the exclusion of the concerning %s(s). "
                        "This allows to ignore services which are known to fail beforehand. </p>"
                    )
                    % unit.singular,
                    add_label=_("Add pattern"),
                ),
            ),
            (
                "activating_levels",
                SimpleLevels(
                    Age,
                    title=_("Define a tolerating time period for activating %s") % unit.plural,
                    help=_(
                        "Choose time levels for which a %s is allowed to be in an 'activating' state"
                    )
                    % unit.plural,
                    default_levels=(30, 60),
                ),
            ),
            (
                "deactivating_levels",
                SimpleLevels(
                    Age,
                    title=_("Define a tolerating time period for deactivating %s") % unit.plural,
                    help=_(
                        "Choose time levels (in seconds) for which a %s is allowed to be in an 'deactivating' state"
                    )
                    % unit.singular,
                    default_value=(30, 60),
                ),
            ),
            (
                "reloading_levels",
                SimpleLevels(
                    Age,
                    title=_("Define a tolerating time period for reloading %s") % unit.plural,
                    help=_(
                        "Choose time levels (in seconds) for which a %s is allowed to be in a 'reloading' state"
                    )
                    % unit.singular,
                    default_value=(30, 60),
                ),
            ),
        ],
        help=_(
            "This ruleset only applies to the Summary Systemd %s and not the individual "
            "Systemd %s."
        )
        % (unit.singular, unit.plural),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="systemd_services_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=lambda: _parameter_valuespec_systemd_units_summary(SERVICE),
        title=lambda: _("Systemd Services Summary"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="systemd_sockets_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=lambda: _parameter_valuespec_systemd_units_summary(SOCKET),
        title=lambda: _("Systemd Sockets Summary"),
    )
)
