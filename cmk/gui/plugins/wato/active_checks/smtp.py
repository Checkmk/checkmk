#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import (
    ip_address_family_element,
    RulespecGroupActiveChecks,
    transform_cert_days,
)
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    FixedValue,
    Float,
    Integer,
    ListOfStrings,
    TextInput,
    Transform,
    Tuple,
)


def _active_checks_smtp_transform_smtp_address_family(val):
    if "ip_version" in val:
        val["address_family"] = val.pop("ip_version")
    return val


def _valuespec_active_checks_smtp():
    return Tuple(
        title=_("Check SMTP service access"),
        help=_(
            "This check uses <tt>check_smtp</tt> from the standard "
            "Nagios plugins in order to try the response of an SMTP "
            "server."
        ),
        elements=[
            TextInput(
                title=_("Name"),
                help=_(
                    "The service description will be <b>SMTP</b> plus this name. If the name starts with "
                    "a caret (<tt>^</tt>), the service description will not be prefixed with <tt>SMTP</tt>."
                ),
                allow_empty=False,
            ),
            Transform(
                valuespec=Dictionary(
                    title=_("Optional parameters"),
                    elements=[
                        (
                            "hostname",
                            TextInput(
                                title=_("DNS Hostname or IP address"),
                                allow_empty=False,
                                help=_(
                                    "You can specify a hostname or IP address different from the IP address "
                                    "of the host as configured in your host properties."
                                ),
                            ),
                        ),
                        (
                            "port",
                            Transform(
                                valuespec=Integer(
                                    title=_("TCP Port to connect to"),
                                    help=_(
                                        "The TCP Port the SMTP server is listening on. "
                                        "The default is <tt>25</tt>."
                                    ),
                                    size=5,
                                    minvalue=1,
                                    maxvalue=65535,
                                    default_value=25,
                                ),
                                forth=int,
                            ),
                        ),
                        ip_address_family_element(),
                        (
                            "expect",
                            TextInput(
                                title=_("Expected String"),
                                help=_(
                                    "String to expect in first line of server response. "
                                    "The default is <tt>220</tt>."
                                ),
                                size=8,
                                allow_empty=False,
                                default_value="220",
                            ),
                        ),
                        (
                            "commands",
                            ListOfStrings(
                                title=_("SMTP Commands"),
                                help=_("SMTP commands to execute."),
                            ),
                        ),
                        (
                            "command_responses",
                            ListOfStrings(
                                title=_("SMTP Responses"),
                                help=_("Expected responses to the given SMTP commands."),
                            ),
                        ),
                        (
                            "from",
                            TextInput(
                                title=_("FROM-Address"),
                                help=_(
                                    "FROM-address to include in MAIL command, required by Exchange 2000"
                                ),
                                size=20,
                                allow_empty=True,
                                default_value="",
                            ),
                        ),
                        (
                            "fqdn",
                            TextInput(
                                title=_("FQDN"),
                                help=_("FQDN used for HELO"),
                                size=20,
                                allow_empty=True,
                                default_value="",
                            ),
                        ),
                        (
                            "cert_days",
                            Transform(
                                valuespec=Tuple(
                                    title=_("Minimum Certificate Age"),
                                    help=_("Minimum number of days a certificate has to be valid"),
                                    elements=[
                                        Integer(
                                            title=_("Warning at or below"),
                                            minvalue=0,
                                            unit=_("days"),
                                        ),
                                        Integer(
                                            title=_("Critical at or below"),
                                            minvalue=0,
                                            unit=_("days"),
                                        ),
                                    ],
                                ),
                                forth=transform_cert_days,
                            ),
                        ),
                        (
                            "starttls",
                            FixedValue(
                                value=True,
                                totext=_("STARTTLS enabled."),
                                title=_("Use STARTTLS for the connection."),
                            ),
                        ),
                        (
                            "auth",
                            Tuple(
                                title=_("Enable SMTP AUTH (LOGIN)"),
                                help=_(
                                    "SMTP AUTH type to check (default none, only LOGIN supported)"
                                ),
                                elements=[
                                    TextInput(
                                        title=_("Username"),
                                        size=12,
                                        allow_empty=False,
                                    ),
                                    IndividualOrStoredPassword(
                                        title=_("Password"),
                                        size=12,
                                        allow_empty=False,
                                    ),
                                ],
                            ),
                        ),
                        (
                            "response_time",
                            Tuple(
                                title=_("Expected response time"),
                                elements=[
                                    Float(
                                        title=_("Warning if above"), unit=_("sec"), allow_int=True
                                    ),
                                    Float(
                                        title=_("Critical if above"), unit=_("sec"), allow_int=True
                                    ),
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
                    ],
                ),
                forth=_active_checks_smtp_transform_smtp_address_family,
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:smtp",
        valuespec=_valuespec_active_checks_smtp,
    )
)
