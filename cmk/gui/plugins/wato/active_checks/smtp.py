#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import ip_address_family_element
from cmk.gui.valuespec import (
    Dictionary,
    FixedValue,
    Float,
    Integer,
    ListOfStrings,
    Migrate,
    NetworkPort,
    TextInput,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupActiveChecks
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_active_checks_smtp() -> Migrate:
    ip_addr_key, ip_addr_vs = ip_address_family_element()
    return Migrate(
        valuespec=Dictionary(
            title=_("Check SMTP service access"),
            help=_(
                "This check uses <tt>check_smtp</tt> from the standard "
                "Nagios plugins in order to try the response of an SMTP "
                "server."
            ),
            elements=[
                (
                    "name",
                    TextInput(
                        title=_("Name"),
                        help=_(
                            "The service description will be <b>SMTP</b> plus this name. If the name starts with "
                            "a caret (<tt>^</tt>), the service description will not be prefixed with <tt>SMTP</tt>."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "hostname",
                    TextInput(
                        title=_("DNS host name or IP address"),
                        allow_empty=False,
                        help=_(
                            "You can specify a host name or IP address different from the IP address "
                            "of the host as configured in your host properties."
                        ),
                    ),
                ),
                (
                    "port",
                    NetworkPort(
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
                ),
                (ip_addr_key, ip_addr_vs),
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
                    "from_address",
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
                    Tuple(
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
                        help=_("SMTP AUTH type to check (default none, only LOGIN supported)"),
                        elements=[
                            TextInput(
                                title=_("Username"),
                                size=12,
                                allow_empty=False,
                            ),
                            MigrateToIndividualOrStoredPassword(
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
                            Float(title=_("Warning if above"), unit=_("sec"), allow_int=True),
                            Float(title=_("Critical if above"), unit=_("sec"), allow_int=True),
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
            optional_keys=[
                "hostname",
                "port",
                ip_addr_key,
                "expect",
                "commands",
                "command_responses",
                "from_address",
                "fqdn",
                "cert_days",
                "starttls",
                "auth",
                "response_time",
                "timeout",
            ],
        ),
        migrate=_migrate,
    )


def _migrate(p: tuple[str, dict[str, object]] | dict[str, object]) -> dict[str, object]:
    """
    >>> _migrate(("my_name", {"from": "1.2.3.4"}))
    {'from_address': '1.2.3.4', 'name': 'my_name'}
    """
    if isinstance(p, dict):
        return p
    name, old_p = p
    new_p = {"from_address" if k == "from" else k: v for k, v in old_p.items()}
    new_p["name"] = name
    return new_p


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("smtp"),
        valuespec=_valuespec_active_checks_smtp,
    )
)
