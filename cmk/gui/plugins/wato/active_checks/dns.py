#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupActiveChecks
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
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


def _transform_check_dns_settings(params: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    >>> _transform_check_dns_settings({'expected_address': '1.2.3.4,C0FE::FE11'})
    {'expect_all_addresses': True, 'expected_addresses_list': ['1.2.3.4', 'C0FE::FE11']}
    >>> _transform_check_dns_settings({'expected_address': ['A,B', 'C']})
    {'expect_all_addresses': True, 'expected_addresses_list': ['A', 'B', 'C']}

    """
    legacy_addresses = params.get("expected_address")
    if legacy_addresses is None:
        return params

    return {
        "expect_all_addresses": True,
        "expected_addresses_list": (
            legacy_addresses.split(",")
            if isinstance(legacy_addresses, str)
            else sum((entry.split(",") for entry in legacy_addresses), [])
        ),
        **{k: v for k, v in params.items() if k != "expected_address"},
    }


def _valuespec_active_checks_dns():
    return Tuple(
        title=_("Check DNS service"),
        help=_(
            "Check the resolution of a hostname into an IP address by a DNS server. "
            "This check uses <tt>check_dns</tt> from the standard Nagios plugins."
        ),
        elements=[
            TextInput(
                title=_("Queried Hostname or IP address"),
                allow_empty=False,
                help=_("The name or IPv4 address you want to query"),
            ),
            Transform(
                valuespec=Dictionary(
                    title=_("Optional parameters"),
                    elements=[
                        (
                            "name",
                            TextInput(
                                title=_("Alternative Service description"),
                                help=_(
                                    "The service description will be this name instead <i>DNS Servername</i>"
                                ),
                            ),
                        ),
                        (
                            "server",
                            Alternative(
                                title=_("DNS Server"),
                                elements=[
                                    FixedValue(
                                        value=None,
                                        totext=_("this host"),
                                        title=_("Use this host as a DNS server for the lookup"),
                                    ),
                                    TextInput(
                                        title=_("Specify DNS Server"),
                                        allow_empty=False,
                                        help=_(
                                            "Optional DNS server you want to use for the lookup"
                                        ),
                                    ),
                                    FixedValue(
                                        value="default DNS server",
                                        totext=_("default DNS server"),
                                        title=_("Use default DNS server"),
                                    ),
                                ],
                            ),
                        ),
                        (
                            "expect_all_addresses",
                            DropdownChoice(
                                title=_("Address matching"),
                                choices=[
                                    (True, _("Expect all of the addresses")),
                                    (False, _("Expect at least one of the addresses")),
                                ],
                            ),
                        ),
                        (
                            "expected_addresses_list",
                            ListOfStrings(
                                title=_("Expected DNS answers"),
                                help=_(
                                    "List all allowed expected answers here. If query for an "
                                    "IP address then the answer will be host names, that end "
                                    "with a dot."
                                ),
                            ),
                        ),
                        (
                            "expected_authority",
                            FixedValue(
                                value=True,
                                title=_("Expect Authoritative DNS Server"),
                                totext=_("Expect Authoritative"),
                            ),
                        ),
                        (
                            "response_time",
                            Tuple(
                                title=_("Expected response time"),
                                elements=[
                                    Float(
                                        title=_("Warning if above"), unit=_("sec"), default_value=1
                                    ),
                                    Float(
                                        title=_("Critical if above"), unit=_("sec"), default_value=2
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
                forth=_transform_check_dns_settings,
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:dns",
        valuespec=_valuespec_active_checks_dns,
    )
)
