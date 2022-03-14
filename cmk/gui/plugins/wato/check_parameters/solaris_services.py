#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextInput,
    Tuple,
)


def _valuespec_inventory_solaris_services_rules():
    return Dictionary(
        title=_("Solaris service discovery"),
        elements=[
            ("descriptions", ListOfStrings(title=_("Descriptions"))),
            ("categories", ListOfStrings(title=_("Categories"))),
            ("names", ListOfStrings(title=_("Names"))),
            ("instances", ListOfStrings(title=_("Instances"))),
            (
                "states",
                ListOf(
                    valuespec=DropdownChoice(
                        choices=[
                            ("online", _("online")),
                            ("disabled", _("disabled")),
                            ("maintenance", _("maintenance")),
                            ("legacy_run", _("legacy run")),
                        ],
                    ),
                    title=_("States"),
                ),
            ),
            (
                "outcome",
                Alternative(
                    title=_("Service name"),
                    elements=[
                        FixedValue(value="full_descr", title=_("Full Description"), totext=""),
                        FixedValue(
                            value="descr_without_prefix",
                            title=_("Description without type prefix"),
                            totext="",
                        ),
                    ],
                ),
            ),
        ],
        help=_(
            "This rule can be used to configure the discovery of the Solaris services check. "
            "You can configure specific Solaris services to be monitored by the Solaris check by "
            "selecting them by description, category, name, or current state during the discovery."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inventory_solaris_services_rules",
        valuespec=_valuespec_inventory_solaris_services_rules,
    )
)


def _parameter_valuespec_solaris_services():
    return Dictionary(
        elements=[
            (
                "additional_servicenames",
                ListOfStrings(
                    title=_("Alternative names for the service"),
                    help=_(
                        "Here you can specify alternative names that the service might have. "
                        "This helps when the exact spelling of the services can changed from "
                        "one version to another."
                    ),
                ),
            ),
            (
                "states",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("Expected state"),
                                choices=[
                                    (None, _("Ignore the state")),
                                    ("online", _("Online")),
                                    ("disabled", _("Disabled")),
                                    ("maintenance", _("Maintenance")),
                                    ("legacy_run", _("Legacy run")),
                                ],
                            ),
                            DropdownChoice(
                                title=_("STIME"),
                                choices=[
                                    (None, _("Ignore")),
                                    (True, _("Has changed")),
                                    (False, _("Did not changed")),
                                ],
                            ),
                            MonitoringState(
                                title=_("Resulting state"),
                            ),
                        ],
                    ),
                    title=_("Services states"),
                    help=_(
                        "You can specify a separate monitoring state for each possible "
                        "combination of service state. If you do not use this parameter, "
                        "then only online/legacy_run will be assumed to be OK."
                    ),
                ),
            ),
            (
                "else",
                MonitoringState(
                    title=_("State if no entry matches"),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="solaris_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the service"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_solaris_services,
        title=lambda: _("Solaris Services"),
    )
)
