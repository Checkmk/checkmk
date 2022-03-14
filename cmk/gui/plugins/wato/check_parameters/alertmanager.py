#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Integer,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextInput,
)


def _discovery_parameters_valuespec_alertmanager():
    return Dictionary(
        title=_("Alertmanager discovery"),
        elements=[
            (
                "group_services",
                CascadingDropdown(
                    title=_("Service creation"),
                    choices=[
                        (
                            True,
                            _("Create services for alert rule groups"),
                            Dictionary(
                                elements=[
                                    (
                                        "min_amount_rules",
                                        Integer(
                                            title=_(
                                                "Minimum amount of alert rules in a group to create a group service"
                                            ),
                                            minvalue=1,
                                            default_value=3,
                                            help=_(
                                                "Below the specified value alert rules will be monitored as a"
                                                "single service."
                                            ),
                                        ),
                                    ),
                                    (
                                        "no_group_services",
                                        ListOfStrings(
                                            title=_(
                                                "Don't create a group service for the following groups"
                                            ),
                                        ),
                                    ),
                                ],
                                optional_keys=[],
                            ),
                        ),
                        (
                            False,
                            _("Create one service per alert rule"),
                            FixedValue(
                                value={},
                                title=_("Enabled"),
                                totext="",
                            ),
                        ),
                    ],
                ),
            ),
            (
                "summary_service",
                FixedValue(
                    value=True,
                    title=_("Create a summary service for all alert rules"),
                    totext="",
                ),
            ),
        ],
        optional_keys=["summary_service"],
        default_keys=["summary_service"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_alertmanager",
        valuespec=_discovery_parameters_valuespec_alertmanager,
        title=lambda: _("Alertmanager discovery"),
    )
)


def valuespec_alert_remapping():
    return ListOf(
        valuespec=Dictionary(
            elements=[
                (
                    "rule_names",
                    ListOfStrings(
                        title=_("Alert rule names"),
                        help=_("A list of rule names as defined in Alertmanager."),
                    ),
                ),
                (
                    "map",
                    Dictionary(
                        title=_("States"),
                        elements=[
                            ("inactive", MonitoringState(title="inactive")),
                            ("pending", MonitoringState(title="pending")),
                            ("firing", MonitoringState(title="firing")),
                            ("none", MonitoringState(title="none")),
                            ("n/a", MonitoringState(title="n/a")),
                        ],
                        optional_keys=[],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        title=_("Remap alert rule states"),
        add_label=_("Add mapping"),
        help=_("Configure the monitoring state for Alertmanager rules."),
        allow_empty=False,
        default_value=[
            {
                "map": {
                    "inactive": 2,
                    "pending": 2,
                    "firing": 0,
                    "none": 2,
                    "n/a": 2,
                },
                "rule_names": ["Watchdog"],
            }
        ],
    )


def _check_parameters_valuespec_alertmanager():
    return Dictionary(
        title=_("Alert mangager rule state"),
        elements=[
            ("alert_remapping", valuespec_alert_remapping()),
        ],
        optional_keys=["alert_remapping"],
        default_keys=["alert_remapping"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="alertmanager_rule_state",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of Alert rules/Alert rule groups"), allow_empty=True
        ),
        match_type="dict",
        parameter_valuespec=_check_parameters_valuespec_alertmanager,
        title=lambda: _("Alertmanager rule states"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="alertmanager_rule_state_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_check_parameters_valuespec_alertmanager,
        title=lambda: _("Alertmanager rule states (Summary)"),
    )
)
