#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    api_request_authentication,
    prometheus_connection,
)
from cmk.gui.plugins.wato.special_agents.common_tls_verification import tls_verify_flag_default_no
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, FixedValue, ListOfStrings, TextInput
from cmk.gui.wato import RulespecGroupVMCloudContainer


def _valuespec_generic_metrics_alertmanager():
    return Dictionary(
        elements=[
            (
                "hostname",
                TextInput(
                    title=_("Optionally forward output to host"),
                    help=_(
                        "If given forward output to a different host using piggyback mechanics."
                    ),
                ),
            ),
            ("connection", prometheus_connection()),
            tls_verify_flag_default_no(),
            api_request_authentication(),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                ),
            ),
            (
                "ignore_alerts",
                Dictionary(
                    title=_("Ignore alert rules"),
                    help=_(
                        "The ignore option can target alert rules on different levels including "
                        "specific rules as well as entire rule groups. Matching rules will be filtered "
                        "out on the alertmanager agent side."
                    ),
                    elements=[
                        (
                            "ignore_na",
                            FixedValue(
                                value=True,
                                title=_("Ignore alert rules with no status"),
                                totext="",
                                help=_(
                                    "Alert rules that don't export a status are ignored with this option."
                                ),
                            ),
                        ),
                        (
                            "ignore_alert_rules",
                            ListOfStrings(
                                title=_("Ignore specific alert rules"),
                                help=_("Name of specific alert rules you want to ignore."),
                            ),
                        ),
                        (
                            "ignore_alert_groups",
                            ListOfStrings(
                                title=_("Ignore all alert rules within certain alert rule groups"),
                            ),
                        ),
                    ],
                    optional_keys=["ignore_na"],
                    default_keys=["ignore_na"],
                ),
            ),
        ],
        title=_("Alertmanager"),
        optional_keys=["auth_basic"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name=RuleGroup.SpecialAgents("alertmanager"),
        valuespec=_valuespec_generic_metrics_alertmanager,
    )
)
