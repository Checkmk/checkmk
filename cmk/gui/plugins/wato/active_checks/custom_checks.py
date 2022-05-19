#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import HostRulespec, PluginCommandLine, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, FixedValue, Integer, TextInput


def _valuespec_custom_checks():
    return Dictionary(
        title=_("Integrate Nagios plugins"),
        help=_(
            'With this ruleset you can configure "classical Monitoring checks" '
            "to be executed directly on your monitoring server. These checks "
            "will not use Check_MK. It is also possible to configure passive "
            "checks that are fed with data from external sources via the "
            "command pipe of the monitoring core."
        )
        + _('This option can only be used with the permission "Can add or modify executables".'),
        elements=[
            (
                "service_description",
                TextInput(
                    title=_("Service description"),
                    help=_(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    allow_empty=False,
                    default_value=_("Customcheck"),
                ),
            ),
            (
                "command_line",
                PluginCommandLine(),
            ),
            (
                "command_name",
                TextInput(
                    title=_("Internal command name"),
                    help=_(
                        "If you want, you can specify a name that will be used "
                        "in the <tt>define command</tt> section for these checks. This "
                        "allows you to a assign a custom PNP template for the performance "
                        "data of the checks. If you omit this, then <tt>check-mk-custom</tt> "
                        "will be used."
                    ),
                    size=32,
                ),
            ),
            (
                "has_perfdata",
                FixedValue(
                    value=True,
                    title=_("Performance data"),
                    totext=_("process performance data"),
                ),
            ),
            (
                "freshness",
                Dictionary(
                    title=_("Check freshness"),
                    help=_(
                        "Freshness checking is only useful for passive checks when the staleness feature "
                        "is not enough for you. It changes the state of a check to a configurable other state "
                        "when the check results are not arriving in time. Staleness will still grey out the "
                        "test after the corrsponding interval. If you don't want that, you might want to adjust "
                        "the staleness interval as well. The staleness interval is calculated from the normal "
                        "check interval multiplied by the staleness value in the <tt>Global Settings</tt>. "
                        "The normal check interval can be configured in a separate rule for your check."
                    ),
                    optional_keys=False,
                    elements=[
                        (
                            "interval",
                            Integer(
                                title=_("Expected update interval"),
                                label=_("Updates are expected at least every"),
                                unit=_("minutes"),
                                minvalue=1,
                                default_value=10,
                            ),
                        ),
                        (
                            "state",
                            DropdownChoice(
                                title=_("State in case of absent updates"),
                                choices=[
                                    (0, _("OK")),
                                    (1, _("WARN")),
                                    (2, _("CRIT")),
                                    (3, _("UNKNOWN")),
                                ],
                                default_value=3,
                            ),
                        ),
                        (
                            "output",
                            TextInput(
                                title=_("Plugin output in case of absent updates"),
                                size=40,
                                allow_empty=False,
                                default_value=_("Check result did not arrive in time"),
                            ),
                        ),
                    ],
                ),
            ),
        ],
        required_keys=["service_description"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="custom_checks",
        valuespec=_valuespec_custom_checks,
    )
)
