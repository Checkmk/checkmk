#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import check_icmp_params, HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DictionaryEntry,
    Hostname,
    Integer,
    TextInput,
    ValueSpec,
)
from cmk.gui.wato import RulespecGroupActiveChecks


def _validate_ip_index(value: int, varprefix: str) -> None:
    if value >= 1:
        return
    raise MKUserError(varprefix, _("The index must be greater or equal to 1."))


def _valuespec_active_checks_icmp() -> ValueSpec:
    elements: list[DictionaryEntry] = [
        (
            "description",
            TextInput(
                title=_("Service description"),
                allow_empty=False,
                default_value="PING",
            ),
        ),
        (
            "address",
            CascadingDropdown(
                title=_("Alternative address to ping"),
                help=_(
                    "If you omit this setting then the configured IP address of that host "
                    "will be pinged. In the host configuration you can provide additional "
                    "addresses besides the main IP address (additional IP addresses section). "
                    "In this option you can select which set of addresses you want to include "
                    'for this check. "Ping additional IP addresses" will omit the host '
                    'configured main address while the "Ping all addresses" option will '
                    "include both the main and additional addresses."
                ),
                orientation="horizontal",
                choices=[
                    ("address", _("Ping the normal IP address")),
                    ("alias", _("Use the alias as DNS name / IP address")),
                    (
                        "explicit",
                        _("Ping the following explicit address / DNS name"),
                        Hostname(),
                    ),
                    ("all_ipv4addresses", _("Ping all IPv4 addresses")),
                    ("all_ipv6addresses", _("Ping all IPv6 addresses")),
                    ("additional_ipv4addresses", _("Ping additional IPv4 addresses")),
                    ("additional_ipv6addresses", _("Ping additional IPv6 addresses")),
                    (
                        "indexed_ipv4address",
                        _("Ping IPv4 address identified by its index (starting at 1)"),
                        Integer(default_value=1, validate=_validate_ip_index),
                    ),
                    (
                        "indexed_ipv6address",
                        _("Ping IPv6 address identified by its index (starting at 1)"),
                        Integer(default_value=1, validate=_validate_ip_index),
                    ),
                ],
            ),
        ),
        (
            "multiple_services",
            Checkbox(
                title=_("Multiple services"),
                label=_("Create a service for every pinged IP address"),
                default_value=False,
            ),
        ),
        (
            "min_pings",
            Integer(
                title=_("Number of positive responses required for OK state"),
                help=_(
                    "When pinging multiple addresses, failure to ping one of the "
                    "provided addresses will lead to a Crit status of the service. "
                    "This option allows to specify the minimum number of successful "
                    "pings which will still classify the service as OK. The smallest "
                    "number is 1 and the maximum number should be (number of addresses - 1). "
                    "A number larger than the suggested number will always lead to a "
                    "Crit Status. One must also select a suitable option from the "
                    '"Alternative address to ping" above.'
                ),
                minvalue=1,
            ),
        ),
    ]
    return Dictionary(
        title=_("Check hosts with PING (ICMP Echo Request)"),
        help=_(
            "This ruleset allows you to configure explicit PING monitoring of hosts. "
            "Usually a PING is being used as a host check, so this is not necessary. "
            "There are some situations, however, where this can be useful. One of them "
            "is when using the Checkmk Micro Core with SMART Ping and you want to "
            "track performance data of the PING to some hosts, nevertheless."
        ),
        elements=elements + check_icmp_params(),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("icmp"),
        valuespec=_valuespec_active_checks_icmp,
    )
)
