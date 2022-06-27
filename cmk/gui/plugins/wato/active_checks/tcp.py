#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupActiveChecks, transform_cert_days
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    ListOfStrings,
    TextInput,
    Transform,
    Tuple,
)


def _valuespec_active_checks_tcp():
    return Tuple(
        title=_("Check TCP port connection"),
        help=_(
            "This check tests the connection to a TCP port. It uses "
            "<tt>check_tcp</tt> from the standard Nagios plugins."
        ),
        elements=[
            Integer(title=_("TCP Port"), minvalue=1, maxvalue=65535),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "svc_description",
                        TextInput(
                            title=_("Service description"),
                            allow_empty=False,
                            help=_(
                                "Here you can specify a service description. "
                                "If this parameter is not set, the service is named <tt>TCP Port [PORT NUMBER]</tt>"
                            ),
                        ),
                    ),
                    (
                        "hostname",
                        TextInput(
                            title=_("DNS Hostname"),
                            allow_empty=False,
                            help=_(
                                "If you specify a hostname here, then a dynamic DNS lookup "
                                "will be done instead of using the IP address of the host "
                                "as configured in your host properties."
                            ),
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
                        "escape_send_string",
                        FixedValue(
                            value=True,
                            title=_(
                                "Expand <tt>\\n</tt>, <tt>\\r</tt> and <tt>\\t</tt> in the sent string"
                            ),
                            totext=_("expand escapes"),
                        ),
                    ),
                    (
                        "expect",
                        ListOfStrings(
                            title=_("Strings to expect in response"),
                            orientation="horizontal",
                            valuespec=TextInput(size=30),
                        ),
                    ),
                    (
                        "expect_all",
                        FixedValue(
                            value=True,
                            totext=_("expect all"),
                            title=_("Expect <b>all</b> of those strings in the response"),
                        ),
                    ),
                    (
                        "jail",
                        FixedValue(
                            value=True,
                            title=_("Hide response from socket"),
                            help=_(
                                "As soon as you configure expected strings in "
                                "the response the check will output the response - "
                                "as long as you do not hide it with this option"
                            ),
                            totext=_("hide response"),
                        ),
                    ),
                    (
                        "mismatch_state",
                        DropdownChoice(
                            title=_("State for expected string mismatch"),
                            choices=[
                                ("crit", _("CRITICAL")),
                                ("warn", _("WARNING")),
                                ("ok", _("OK")),
                            ],
                        ),
                    ),
                    (
                        "delay",
                        Integer(
                            title=_("Seconds to wait before polling"),
                            help=_(
                                "Seconds to wait between sending string and polling for response"
                            ),
                            unit=_("sec"),
                            default_value=0,
                        ),
                    ),
                    (
                        "maxbytes",
                        Integer(
                            title=_("Maximum number of bytes to receive"),
                            help=_(
                                "Close connection once more than this number of "
                                "bytes are received. Per default the number of "
                                "read bytes is not limited. This setting is only "
                                "used if you expect strings in the response."
                            ),
                            default_value=1024,
                        ),
                    ),
                    (
                        "ssl",
                        FixedValue(
                            value=True, totext=_("use SSL"), title=_("Use SSL for the connection.")
                        ),
                    ),
                    (
                        "cert_days",
                        Transform(
                            valuespec=Tuple(
                                title=_("SSL certificate validation"),
                                help=_("Minimum number of days a certificate has to be valid"),
                                elements=[
                                    Integer(
                                        title=_("Warning at or below"), minvalue=0, unit=_("days")
                                    ),
                                    Integer(
                                        title=_("Critical at or below"), minvalue=0, unit=_("days")
                                    ),
                                ],
                            ),
                            forth=transform_cert_days,
                        ),
                    ),
                    (
                        "quit_string",
                        TextInput(
                            title=_("Final string to send"),
                            help=_(
                                "String to send server to initiate a clean close of "
                                "the connection"
                            ),
                            size=30,
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:tcp",
        valuespec=_valuespec_active_checks_tcp,
    )
)
