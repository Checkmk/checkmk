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
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary, ListOf, MonitoringState, RegExp


def _parameter_valuespec_systemd_services():
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
                                title=_("Monitoring state if service is active"),
                                default_value=0,
                            ),
                        ),
                        (
                            "inactive",
                            MonitoringState(
                                title=_("Monitoring state if service is inactive"),
                                default_value=0,
                            ),
                        ),
                        (
                            "failed",
                            MonitoringState(
                                title=_("Monitoring state if service is failed"),
                                default_value=2,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "states_default",
                MonitoringState(
                    title=_("Monitoring state for any other service state"),
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
                    title=_("Exclude services matching provided regex patterns"),
                    help=_(
                        "<p>You can optionally define one or multiple regular expressions "
                        "where a matching case will result in the exclusion of the concerning service(s). "
                        "This allows to ignore services which are known to fail beforehand. </p>"
                    ),
                    add_label=_("Add pattern"),
                ),
            ),
            (
                "activating_levels",
                SimpleLevels(
                    Age,
                    title=_("Define a tolerating time period for activating services"),
                    help=_(
                        "Choose time levels for which a service is allowed to be in an 'activating' state"
                    ),
                    default_levels=(30, 60),
                ),
            ),
            (
                "deactivating_levels",
                SimpleLevels(
                    Age,
                    title=_("Define a tolerating time period for deactivating services"),
                    help=_(
                        "Choose time levels (in seconds) for which a service is allowed to be in an 'deactivating' state"
                    ),
                    default_value=(30, 60),
                ),
            ),
            (
                "reloading_levels",
                SimpleLevels(
                    Age,
                    title=_("Define a tolerating time period for reloading services"),
                    help=_(
                        "Choose time levels (in seconds) for which a service is allowed to be in a 'reloading' state"
                    ),
                    default_value=(30, 60),
                ),
            ),
        ],
        help=_(
            "This ruleset only applies to the Summary Systemd service and not the individual "
            "Systemd services."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="systemd_services_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_services,
        title=lambda: _("Systemd Services Summary"),
    )
)
