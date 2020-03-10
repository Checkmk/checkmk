#!/usr/bin/env python
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
    RegExpUnicode,
    RegExp,
    TextAscii,
    Tuple,
    Integer,
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
        title=_("Systemd Service Discovery"),
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
    return Dictionary(elements=[
        ("ignored",
         ListOf(
             RegExpUnicode(
                 title=_("Pattern (Regex)"),
                 size=40,
                 mode=RegExp.infix,
             ),
             title=_("Exclude services matching provided regex patterns"),
             help=_(
                 '<p>You can optionally define one or multiple regular expressions '
                 'where a matching case will result in the exclusion of the concerning service(s). '
                 'This allows to ignore services which are known to fail beforehand. </p>'),
             add_label=_("Add pattern"),
         )),
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
        ("activating_levels",
         Tuple(
             title=_("Define a tolerating time period for activating services"),
             help=
             _("Choose time levels (in seconds) for which a service is allowed to be in an 'activating' state"
              ),
             elements=[
                 Integer(title=_("Warning at"), unit=_("seconds"), default_value=30),
                 Integer(title=_("Critical at"), unit=_("seconds"), default_value=60),
             ])),
        ("reloading_levels",
         Tuple(
             title=_("Define a tolerating time period for reloading services"),
             help=
             _("Choose time levels (in seconds) for which a service is allowed to be in a 'reloading' state"
              ),
             elements=[
                 Integer(title=_("Warning at"), unit=_("seconds"), default_value=30),
                 Integer(title=_("Critical at"), unit=_("seconds"), default_value=60),
             ])),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="systemd_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of the service")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_services,
        title=lambda: _("Systemd Services"),
    ))
