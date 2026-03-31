#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Filename,
    FixedValue,
    Hostname,
    ListOf,
    ListOfNetworkPorts,
    NetworkPort,
    Optional,
    TextInput,
    Tuple,
)
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_apache_status() -> CascadingDropdown:
    return CascadingDropdown(
        title=_("Apache web servers (Linux)"),
        help=_(
            "If you activate this option, then the agent plug-in <tt>apache_status</tt> will be deployed. "
            "For each configured or detected Apache instance there will be one new service with detailed "
            "statistics of the current number of clients and processes and their various states."
        ),
        choices=[
            (
                "autodetect",
                _("Autodetect instances, expect HTTPs on the following ports:"),
                ListOfNetworkPorts(
                    title=None,
                    default_value=[443],
                ),
            ),
            (
                "static",
                _("Specific list of instances"),
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            CascadingDropdown(
                                title=_("Protocol"),
                                choices=[
                                    (
                                        "http",
                                        _("HTTP"),
                                        FixedValue(
                                            # HTTP does not use CA certs.
                                            value=None,
                                            totext="",
                                        ),
                                    ),
                                    (
                                        "https",
                                        _("HTTPS"),
                                        Optional(
                                            valuespec=Filename(
                                                default="/etc/ssl/certs/cert.pem",
                                                help=_("An absolute path to a CA certificate"),
                                                size=40,
                                            ),
                                            title=_("CA certificate"),
                                            label=_("Path to a CA certificate"),
                                            none_label=_("No certificate"),
                                            sameline=True,
                                        ),
                                    ),
                                ],
                            ),
                            Hostname(
                                title=_("IPv4 address"),
                                default_value="127.0.0.1",
                            ),
                            Alternative(
                                elements=[
                                    FixedValue(
                                        value=None,
                                        title=_("Don't use custom port"),
                                        totext=_("Use default port"),
                                    ),
                                    NetworkPort(
                                        title=_("TCP Port Number"),
                                        default_value=80,
                                    ),
                                ]
                            ),
                            TextInput(
                                title=_("Name of the instance in the monitoring"),
                                help=_(
                                    "If you do not specify a name here, then the TCP port number "
                                    "will be used as an instance name."
                                ),
                            ),
                        ]
                    ),
                ),
            ),
            (None, _("Do not deploy the Apache Status plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("apache_status"),
        valuespec=_valuespec_agent_config_apache_status,
    )
)
