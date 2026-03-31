#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    IPAddress,
    ListOf,
    ListOfNetworkPorts,
    NetworkPort,
    TextInput,
)
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_nginx_status() -> CascadingDropdown:
    return CascadingDropdown(
        title=_("NGINX web servers (Linux)"),
        help=_(
            "If you activate this option, then the agent plug-in <tt>nginx_status</tt> will be deployed. "
            "For each configured or detected NGINX instance there will be one new service with detailed "
            "statistics of the current number of clients and processes and their various states."
        ),
        choices=[
            (
                "autodetect",
                _("Autodetect instances, expect HTTPS on the following ports:"),
                ListOfNetworkPorts(
                    title=None,
                    default_value=[443],
                ),
            ),
            (
                "static",
                _("Specific list of instances"),
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "protocol",
                                DropdownChoice(
                                    title=_("Protocol"),
                                    choices=[
                                        ("http", _("HTTP")),
                                        ("https", _("HTTPS")),
                                    ],
                                ),
                            ),
                            (
                                "address",
                                IPAddress(
                                    title=_("IP address (IPv4 or IPv6)"),
                                    default_value="127.0.0.1",
                                ),
                            ),
                            (
                                "port",
                                NetworkPort(
                                    title=_("TCP port number"),
                                    default_value=80,
                                ),
                            ),
                            (
                                "page",
                                TextInput(
                                    title=_("URI (page name)"),
                                    default_value="nginx_status",
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=["page"],
                    ),
                    add_label=_("Add NGINX instance"),
                ),
            ),
            (None, _("Do not deploy the NGINX status plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("nginx_status"),
        valuespec=_valuespec_agent_config_nginx_status,
    )
)
