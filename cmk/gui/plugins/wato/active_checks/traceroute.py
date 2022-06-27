#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import (
    ip_address_family_element,
    RulespecGroupActiveChecks,
    transform_add_address_family,
)
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DropdownChoice,
    ListOf,
    TextInput,
    Transform,
    Tuple,
)


def _valuespec_active_checks_traceroute():
    return Transform(
        valuespec=Dictionary(
            title=_("Check current routing"),
            help=_(
                "This active check uses <tt>traceroute</tt> in order to determine the current "
                "routing from the monitoring host to the target host. You can specify any number "
                "of missing or expected routes in order to detect e.g. an (unintended) failover "
                "to a secondary route."
            ),
            elements=[
                (
                    "dns",
                    Checkbox(
                        title=_("Name resolution"),
                        label=_("Use DNS to convert IP addresses into hostnames"),
                        help=_(
                            "If you use this option, then <tt>traceroute</tt> is <b>not</b> being "
                            "called with the option <tt>-n</tt>. That means that all IP addresses "
                            "are tried to be converted into names. This usually adds additional "
                            "execution time. Also DNS resolution might fail for some addresses."
                        ),
                    ),
                ),
                ip_address_family_element(),
                (
                    "routers",
                    ListOf(
                        valuespec=Tuple(
                            elements=[
                                TextInput(
                                    title=_("Router (FQDN, IP-Address)"),
                                    allow_empty=False,
                                ),
                                DropdownChoice(
                                    title=_("How"),
                                    choices=[
                                        ("W", _("WARN - if this router is not being used")),
                                        ("C", _("CRIT - if this router is not being used")),
                                        ("w", _("WARN - if this router is being used")),
                                        ("c", _("CRIT - if this router is being used")),
                                    ],
                                ),
                            ]
                        ),
                        title=_("Router that must or must not be used"),
                        add_label=_("Add Condition"),
                    ),
                ),
                (
                    "method",
                    DropdownChoice(
                        title=_("Method of probing"),
                        choices=[
                            (None, _("UDP (default behaviour of traceroute)")),
                            ("icmp", _("ICMP Echo Request")),
                            ("tcp", _("TCP SYN")),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=transform_add_address_family,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:traceroute",
        valuespec=_valuespec_active_checks_traceroute,
    )
)
