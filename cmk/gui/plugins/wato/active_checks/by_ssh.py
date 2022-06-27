#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, Integer, TextInput, Tuple


def _valuespec_active_checks_by_ssh():
    return Tuple(
        title=_("Check via SSH service"),
        help=_("Checks via SSH. "),
        elements=[
            TextInput(
                title=_("Command"),
                help=_("Command to execute on remote host."),
                allow_empty=False,
                size=50,
            ),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "description",
                        TextInput(
                            title=_("Service Description"),
                            help=_(
                                "Must be unique for every host. Defaults to command that is executed."
                            ),
                            size=50,
                        ),
                    ),
                    (
                        "hostname",
                        TextInput(
                            title=_("DNS Hostname or IP address"),
                            default_value="$HOSTADDRESS$",
                            allow_empty=False,
                            help=_(
                                "You can specify a hostname or IP address different from IP address "
                                "of the host as configured in your host properties."
                            ),
                        ),
                    ),
                    (
                        "port",
                        Integer(
                            title=_("SSH Port"),
                            help=_("Default is 22."),
                            minvalue=1,
                            maxvalue=65535,
                            default_value=22,
                        ),
                    ),
                    (
                        "ip_version",
                        Alternative(
                            title=_("IP-Version"),
                            elements=[
                                FixedValue(value="ipv4", totext="", title=_("IPv4")),
                                FixedValue(value="ipv6", totext="", title=_("IPv6")),
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
                        "logname",
                        TextInput(
                            title=_("Username"), help=_("SSH user name on remote host"), size=30
                        ),
                    ),
                    (
                        "identity",
                        TextInput(
                            title=_("Keyfile"), help=_("Identity of an authorized key"), size=50
                        ),
                    ),
                    (
                        "accept_new_host_keys",
                        FixedValue(
                            value=True,
                            title=_("Enable automatic host key acceptance"),
                            help=_(
                                "This will automatically accept hitherto-unseen keys"
                                "but will refuse connections for changed or invalid hostkeys"
                            ),
                            totext=_(
                                "Automatically stores the host key with no manual input requirement"
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:by_ssh",
        valuespec=_valuespec_active_checks_by_ssh,
    )
)
