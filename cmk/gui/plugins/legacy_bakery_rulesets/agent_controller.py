#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupMonitoringAgentsGenericOptions,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, FixedValue, Migrate
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_agent_controller() -> Dictionary:
    return Dictionary(
        title=_("Agent Controller"),
        elements=[
            (
                "agent_ctl_enabled",
                _valuspec_controller_deployment_with_migrate(),
            ),
        ],
        optional_keys=[],
    )


def _valuspec_controller_deployment_with_migrate() -> Migrate:
    return Migrate(
        valuespec=_valuspec_controller_deployment(),
        migrate=lambda v: (
            {
                True: (True, {}),
                False: (False, None),
            }[v]
            if isinstance(v, bool)
            else v
        ),
    )


def _valuspec_controller_deployment() -> CascadingDropdown:
    return CascadingDropdown(
        title=_("Agent Controller deployment"),
        choices=[
            (
                True,
                _("Enable controller"),
                Dictionary(
                    elements=[
                        (
                            "detect_proxy",
                            CascadingDropdown(
                                title=_("Configure proxy server usage"),
                                help=_(
                                    "By default, the Controller ignores proxy servers configured "
                                    "on the target system and connects directly (e.g. when querying "
                                    "the Agent Receiver port from the Checkmk REST API)."
                                ),
                                choices=[
                                    (
                                        False,
                                        _("Ignore proxies configured on the target system"),
                                    ),
                                    (
                                        True,
                                        _("Detect and use proxies configured on the target system"),
                                    ),
                                ],
                                sorted=False,
                            ),
                        ),
                        (
                            "validate_api_cert",
                            CascadingDropdown(
                                title=_(
                                    "Configure TLS certificate validation for querying the "
                                    "Agent Receiver port from the Checkmk REST API"
                                ),
                                help=_(
                                    "By default, certificate validation is disabled because it is not "
                                    "security-relevant at this stage, see "
                                    '<a href="https://checkmk.com/werk/14715" target="_blank">werk #14715</a>.'
                                ),
                                choices=[
                                    (
                                        False,
                                        _("Do not validate server certificate during port query"),
                                    ),
                                    (
                                        True,
                                        _("Validate server certificate during port query"),
                                    ),
                                ],
                                sorted=False,
                            ),
                        ),
                    ],
                ),
            ),
            (
                False,
                _("Disable controller"),
                FixedValue(None, totext=""),
            ),
        ],
        sorted=False,
        default_value=(True, {}),
        help=_(
            "The Agent Controller provides a safe channel for the communication between "
            "the monitoring site and the agent. It also provides the possibility to push "
            "monitoring data to the site (if applicable in your Checkmk edition). "
            "You may disable the Agent Controller if you experience problems with it. "
            "In this case the agent will work in legacy pull mode. Please note: "
            "In the legacy pull mode the transported data is not encrypted."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsGenericOptions,
        name=RuleGroup.AgentConfig("agent_controller"),
        valuespec=_valuespec_agent_config_agent_controller,
    )
)
