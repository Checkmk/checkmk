#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    Dictionary,
    ListChoice,
    ListOf,
    MonitoringState,
    TextInput,
    TextOrRegExp,
)


def _valuespec_discovery_systemd_units_services_rules() -> Dictionary:
    return Dictionary(
        title=_("Systemd single services discovery"),
        elements=[
            (
                "descriptions",
                ListOf(
                    valuespec=TextOrRegExp(),
                    title=_("Restrict by description"),
                    help=_("Restrict the systemd services by description."),
                    allow_empty=False,
                ),
            ),
            (
                "names",
                ListOf(
                    valuespec=TextOrRegExp(),
                    title=_("Restrict by service unit name"),
                    help=_("Restrict the systemd services by unit name."),
                    allow_empty=False,
                ),
            ),
            (
                "states",
                ListChoice(
                    choices=[
                        ("active", "active"),
                        ("inactive", "inactive"),
                        ("failed", "failed"),
                    ],
                    title=_("Restrict by state"),
                    allow_empty=False,
                ),
            ),
        ],
        help=_(
            "Configure the discovery of single systemd services. To be discovered, a service "
            "must match at least one description condition, one name condition and one state "
            "condition, if configured. To simply discover all systemd services, do not "
            "configure any restrictions. Note that independently of this ruleset, some systemd "
            "service units which are used by the Checkmk agent ('check-mk-agent@...') will "
            "never be discovered because they appear and disappear frequently."
        ),
        empty_text=_("No restrictions (discover all systemd service units)"),
    )


rulespec_registry.register(
    HostRulespec(
        is_deprecated=True,
        title=lambda: _("Systemd single services discovery"),
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_systemd_units_services_rules",
        valuespec=_valuespec_discovery_systemd_units_services_rules,
    )
)


def _valuespec_discovery_systemd_units() -> Dictionary:
    return Dictionary(
        title=_("Systemd single unit discovery"),
        elements=[
            (
                "descriptions",
                ListOf(
                    valuespec=TextOrRegExp(),
                    title=_("Restrict by description"),
                    help=_("Restrict the systemd units by description."),
                    allow_empty=False,
                ),
            ),
            (
                "names",
                ListOf(
                    valuespec=TextOrRegExp(),
                    title=_("Restrict by name"),
                    help=_("Restrict the systemd units by their name."),
                    allow_empty=False,
                ),
            ),
            (
                "states",
                ListChoice(
                    choices=[
                        ("active", "active"),
                        ("inactive", "inactive"),
                        ("failed", "failed"),
                    ],
                    title=_("Restrict by state"),
                    allow_empty=False,
                ),
            ),
        ],
        help=_(
            "Configure the discovery of single systemd units (sockets or services)."
            " To be discovered, a unit must match at least one condition each:"
            " One description condition, one name condition and one state condition, if configured."
            " To discover all units, do not configure any restrictions."
            " Independently of this ruleset, some systemd units created by the Checkmk agent"
            " ('check-mk-agent@...') will never be discovered."
            " They appear and disappear frequently."
        ),
        empty_text=_("No restrictions (discover all units)"),
    )


rulespec_registry.register(
    HostRulespec(
        title=lambda: _("Systemd single service discovery"),
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_systemd_units_services",
        valuespec=_valuespec_discovery_systemd_units,
    )
)

rulespec_registry.register(
    HostRulespec(
        title=lambda: _("Systemd single socket discovery"),
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_systemd_units_sockets",
        valuespec=_valuespec_discovery_systemd_units,
    )
)


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
                "else",
                MonitoringState(
                    title=_("Monitoring state if a monitored service is not found at all."),
                    default_value=2,
                ),
            ),
        ],
        help=_(
            "This ruleset only applies when individual Systemd services are discovered. "
            "The user needs to configure this option in the discovery section."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        is_deprecated=True,
        check_group_name="systemd_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the service")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_services,
        title=lambda: _("Systemd single services"),
    )
)


def _parameter_valuespec_systemd_units() -> Dictionary:
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
                "else",
                MonitoringState(
                    title=_("Monitoring state if a monitored unit is not found at all."),
                    default_value=2,
                ),
            ),
        ],
        help=_(
            "This ruleset only applies when individual Systemd units are discovered. "
            "The user needs to configure this option in the discovery section."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="systemd_units_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the service")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_units,
        title=lambda: _("Systemd single service"),
    )
)
rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="systemd_units_sockets",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the socket")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_units,
        title=lambda: _("Systemd single socket"),
    )
)
