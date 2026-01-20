#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, NetworkPort, TextInput
from cmk.gui.wato import RulespecGroupIntegrateOtherServices
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_active_checks_ssh() -> Dictionary:
    return Dictionary(
        title=_("Check SSH service"),
        help=_("This rulset allow you to configure a SSH check for a host"),
        elements=[
            (
                "description",
                TextInput(
                    title=_("Service name"),
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("TCP port number"),
                    default_value=22,
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Connect timeout"),
                    help=_("Seconds before connection times out"),
                    default_value=10,
                ),
            ),
            (
                "remote_version",
                TextInput(
                    title=_("Version of Server"),
                    help=_(
                        "Warn if string doesn't match expected server version (ex: OpenSSH_3.9p1)"
                    ),
                ),
            ),
            (
                "remote_protocol",
                TextInput(
                    title=_("Protocol of Server"),
                    help=_("Warn if protocol doesn't match expected protocol version (ex: 2.0)"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name=RuleGroup.ActiveChecks("ssh"),
        valuespec=_valuespec_active_checks_ssh,
    )
)
