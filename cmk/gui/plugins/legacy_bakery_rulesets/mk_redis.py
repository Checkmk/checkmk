#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Hostname,
    ListOf,
    Migrate,
    NetworkPort,
    TextInput,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _migrate(value: object) -> Any:
    """
    >>> _migrate(("instance", "host", 4444, "pa$$word"))
    {'instance': 'instance', 'password': 'pa$$word', 'connection': ('tcp', {'host': 'host', 'port': 4444})}
    """
    if isinstance(value, tuple):
        instance, host, port, password = value
        return {
            "instance": instance,
            "password": password,
            "connection": ("tcp", {"host": host, "port": port}),
        }
    return value


def _valuespec_agent_config_mk_redis() -> CascadingDropdown:
    return CascadingDropdown(
        title=_("Redis databases"),
        help=_(
            "If you activate this option, then the agent plug-in <tt>mk_redis</tt> will be deployed. "
            "You can configure multiple instances or auto detect running instances."
        ),
        choices=[
            ("autodetect", _("Autodetect instances")),
            (
                "static",
                _("Specific list of instances"),
                ListOf(
                    Migrate(
                        valuespec=Dictionary(
                            elements=[
                                (
                                    "instance",
                                    TextInput(
                                        title=_("Name of the instance in the monitoring"),
                                        allow_empty=False,
                                    ),
                                ),
                                (
                                    "connection",
                                    CascadingDropdown(
                                        title=_("Connection"),
                                        choices=[
                                            (
                                                "tcp",
                                                _("TCP"),
                                                Dictionary(
                                                    elements=[
                                                        (
                                                            "host",
                                                            Hostname(
                                                                title=_("IPv4 address"),
                                                                default_value="127.0.0.1",
                                                                allow_empty=False,
                                                            ),
                                                        ),
                                                        (
                                                            "port",
                                                            NetworkPort(
                                                                title=_("TCP port number"),
                                                                default_value=6379,
                                                            ),
                                                        ),
                                                    ],
                                                    optional_keys=False,
                                                ),
                                            ),
                                            (
                                                "unix-socket",
                                                _("Unix socket"),
                                                Dictionary(
                                                    elements=[
                                                        (
                                                            "socket",
                                                            TextInput(
                                                                title=_("Path to Unix socket"),
                                                                allow_empty=False,
                                                            ),
                                                        ),
                                                    ],
                                                    optional_keys=False,
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                                (
                                    "password",
                                    Alternative(
                                        title=_("Password"),
                                        elements=[
                                            FixedValue(
                                                value=None,
                                                title=_("Don't use password"),
                                                totext=_("Connect without password"),
                                            ),
                                            MigrateToIndividualOrStoredPassword(
                                                title=_("Password"),
                                                allow_empty=False,
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                            optional_keys=False,
                        ),
                        migrate=_migrate,
                    ),
                ),
            ),
            (None, _("Do not deploy the Redis plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_redis"),
        valuespec=_valuespec_agent_config_mk_redis,
    )
)
