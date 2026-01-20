#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    Migrate,
    NetworkPort,
    TextInput,
    Tuple,
)
from cmk.gui.wato import RulespecGroupIntegrateOtherServices
from cmk.utils.rulesets.definition import RuleGroup


# TODO: un-nest the parameters. No need for a dict in a tuple in a dict.
def _valuespec_active_checks_by_ssh() -> Migrate[dict[str, Any]]:
    def to_valuespec(x: tuple[str, dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        return {"options": x} if isinstance(x, tuple) else x

    return Migrate(
        valuespec=Dictionary(
            title=_("Check via SSH service"),
            optional_keys=[],
            elements=[
                (
                    "options",
                    Tuple(
                        title=_("Options"),
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
                                            title=_("Service name"),
                                            help=_(
                                                "Must be unique for every host. Defaults to command that is executed."
                                            ),
                                            size=50,
                                        ),
                                    ),
                                    (
                                        "hostname",
                                        TextInput(
                                            title=_("DNS host name or IP address"),
                                            default_value="$HOSTADDRESS$",
                                            allow_empty=False,
                                            help=_(
                                                "You can specify a host name or IP address different from the IP address of the host as configured in your host properties."
                                            ),
                                        ),
                                    ),
                                    (
                                        "port",
                                        NetworkPort(
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
                                                FixedValue(
                                                    value="ipv4", totext="", title=_("IPv4")
                                                ),
                                                FixedValue(
                                                    value="ipv6", totext="", title=_("IPv6")
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
                                    (
                                        "logname",
                                        TextInput(
                                            title=_("Username"),
                                            help=_("SSH username on remote host"),
                                            size=30,
                                        ),
                                    ),
                                    (
                                        "identity",
                                        TextInput(
                                            title=_("Keyfile"),
                                            help=_("Identity of an authorized key"),
                                            size=50,
                                        ),
                                    ),
                                    (
                                        "accept_new_host_keys",
                                        FixedValue(
                                            value=True,
                                            title=_(
                                                "Enable automatic host key acceptance (OpenSSH version >= 7.6)"
                                            ),
                                            help=_(
                                                "This will automatically accept hitherto-unseen keys, but will refuse connections for changed or invalid host keys. This option only works with OpenSSH version >= 7.6."
                                            ),
                                            totext=_(
                                                "Automatically stores the host key with no manual input requirement"
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            ],
        ),
        migrate=to_valuespec,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name=RuleGroup.ActiveChecks("by_ssh"),
        valuespec=_valuespec_active_checks_by_ssh,
    )
)
