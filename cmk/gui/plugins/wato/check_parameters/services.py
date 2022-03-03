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
    UserIconOrAction,
)
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextInput,
    Tuple,
)


def _valuespec_inventory_services_rules():
    return Dictionary(
        title=_("Windows service discovery"),
        elements=[
            (
                "services",
                ListOfStrings(
                    title=_("Services (Regular Expressions)"),
                    help=_(
                        "Regular expressions matching the begining of the internal name "
                        "or the description of the service. "
                        "If no name is given then this rule will match all services. The "
                        "match is done on the <i>beginning</i> of the service name. It "
                        "is done <i>case sensitive</i>. You can do a case insensitive match "
                        "by prefixing the regular expression with <tt>(?i)</tt>. Example: "
                        "<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> "
                        "or <tt>MsSQL</tt> or <tt>mssql</tt> or..."
                    ),
                    orientation="horizontal",
                ),
            ),
            (
                "state",
                DropdownChoice(
                    choices=[
                        ("running", _("Running")),
                        ("stopped", _("Stopped")),
                    ],
                    title=_("Create check if service is in state"),
                ),
            ),
            (
                "start_mode",
                DropdownChoice(
                    choices=[
                        ("auto", _("Automatic")),
                        ("demand", _("Manual")),
                        ("disabled", _("Disabled")),
                    ],
                    title=_("Create check if service is in start mode"),
                ),
            ),
        ],
        help=_(
            "This rule can be used to configure the inventory of the windows services check. "
            "You can configure specific windows services to be monitored by the windows check by "
            "selecting them by name, current state during the inventory, or start mode."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inventory_services_rules",
        valuespec=_valuespec_inventory_services_rules,
    )
)


def _item_spec_services():
    return TextInput(
        title=_("Name of the service"),
        help=_(
            "Please Please note, that the agent replaces spaces in "
            "the service names with underscores. If you are unsure about the "
            "correct spelling of the name then please look at the output of "
            "the agent (cmk -d HOSTNAME). The service names  are in the first "
            "column of the section &lt;&lt;&lt;services&gt;&gt;&gt;. Please "
            "do not mix up the service name with the display name of the service."
            "The latter one is just being displayed as a further information."
        ),
        allow_empty=False,
    )


def _parameter_valuespec_services():
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
                                default_value="running",
                                choices=[
                                    (None, _("ignore the state")),
                                    ("running", _("running")),
                                    ("stopped", _("stopped")),
                                ],
                            ),
                            DropdownChoice(
                                title=_("Start type"),
                                default_value="auto",
                                choices=[
                                    (None, _("ignore the start type")),
                                    ("demand", _("demand")),
                                    ("disabled", _("disabled")),
                                    ("auto", _("auto")),
                                    ("unknown", _("unknown (old agent)")),
                                ],
                            ),
                            MonitoringState(
                                title=_("Resulting state"),
                            ),
                        ],
                        default_value=("running", "auto", 0),
                    ),
                    title=_("Services states"),
                    help=_(
                        "You can specify a separate monitoring state for each possible "
                        "combination of service state and start type. If you do not use "
                        "this parameter, then only running/auto will be assumed to be OK."
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
            (
                "icon",
                UserIconOrAction(
                    title=_("Add custom icon or action"),
                    help=_(
                        "You can assign icons or actions to the found services in the status GUI."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_services,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_services,
        title=lambda: _("Windows Services"),
    )
)
