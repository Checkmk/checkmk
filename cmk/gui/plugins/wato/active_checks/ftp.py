#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    ListOfStrings,
    NetworkPort,
    TextInput,
    Tuple,
)
from cmk.gui.wato import RulespecGroupActiveChecks
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_active_checks_ftp() -> Dictionary:
    return Dictionary(
        title=_("Check FTP Service"),
        elements=[
            (
                "port",
                NetworkPort(
                    title=_("Portnumber"),
                    default_value=21,
                ),
            ),
            (
                "response_time",
                Tuple(
                    title=_("Expected response time"),
                    elements=[
                        Float(title=_("Warning if above"), unit="ms", default_value=100.0),
                        Float(title=_("Critical if above"), unit="ms", default_value=200.0),
                    ],
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Seconds before connection times out"),
                    unit=_("sec"),
                    default_value=10,
                ),
            ),
            (
                "refuse_state",
                DropdownChoice(
                    title=_("State for connection refusal"),
                    choices=[
                        ("crit", _("CRITICAL")),
                        ("warn", _("WARNING")),
                        ("ok", _("OK")),
                    ],
                ),
            ),
            ("send_string", TextInput(title=_("String to send"), size=30)),
            (
                "expect",
                ListOfStrings(
                    title=_("Strings to expect in response"),
                    orientation="horizontal",
                    valuespec=TextInput(size=30),
                ),
            ),
            (
                "ssl",
                FixedValue(value=True, totext=_("use SSL"), title=_("Use SSL for the connection.")),
            ),
            (
                "cert_days",
                Tuple(
                    title=_("SSL certificate validation"),
                    help=_("Minimum number of days a certificate has to be valid"),
                    elements=[
                        Integer(title=_("Warning at or below"), minvalue=0, unit=_("days")),
                        Integer(title=_("Critical at or below"), minvalue=0, unit=_("days")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("ftp"),
        valuespec=_valuespec_active_checks_ftp,
    )
)
