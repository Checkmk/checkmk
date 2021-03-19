#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    HostRulespec,
)


def _valuespec_discovery_systemd_units_services_rules():
    return Dictionary(
        title=_("Systemd single services siscovery"),
        elements=[
            ('descriptions', ListOfStrings(title=_("Descriptions"))),
            ('names', ListOfStrings(title=_("Service unit names"))),
            ('states',
             ListOf(
                 DropdownChoice(choices=[
                     ("active", "active"),
                     ("inactive", "inactive"),
                     ("failed", "failed"),
                 ],),
                 title=_("States"),
             )),
        ],
        help=_('This rule can be used to configure the discovery of the Linux services check. '
               'You can configure specific Linux services to be monitored by the Linux check by '
               'selecting them by description, unit name, or current state during the discovery.'),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_systemd_units_services_rules",
        valuespec=_valuespec_discovery_systemd_units_services_rules,
    ))


def _parameter_valuespec_systemd_services():
    return Dictionary(
        elements=[
            ("states",
             Dictionary(
                 title=_("Map systemd states to monitoring states"),
                 elements=[
                     ("active",
                      MonitoringState(
                          title=_("Monitoring state if service is active"),
                          default_value=0,
                      )),
                     ("inactive",
                      MonitoringState(
                          title=_("Monitoring state if service is inactive"),
                          default_value=0,
                      )),
                     ("failed",
                      MonitoringState(
                          title=_("Monitoring state if service is failed"),
                          default_value=2,
                      )),
                 ],
             )),
            ("states_default",
             MonitoringState(
                 title=_("Monitoring state for any other service state"),
                 default_value=2,
             )),
            ("else",
             MonitoringState(
                 title=_("Monitoring state if a monitored service is not found at all."),
                 default_value=2,
             )),
        ],
        help=_(
            "This ruleset only applies when individual Systemd services are discovered. The user "
            "needs to configure this option in the discovery section."))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="systemd_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of the service")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_services,
        title=lambda: _("Systemd single services"),
    ))
