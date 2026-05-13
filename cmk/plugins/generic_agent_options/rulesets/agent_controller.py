#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _agent_ctl_enabled_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Agent Controller deployment"),
        help_text=Help(
            "The Agent Controller provides a safe channel for the communication between "
            "the monitoring site and the agent. It also provides the possibility to push "
            "monitoring data to the site (if applicable in your Checkmk edition). "
            "You may disable the Agent Controller if you experience problems with it. "
            "In this case the agent will work in legacy pull mode. Please note: "
            "In the legacy pull mode the transported data is not encrypted."
        ),
        prefill=DefaultValue("enabled"),
        elements=(
            CascadingSingleChoiceElement(
                name="enabled",
                title=Title("Enable controller"),
                parameter_form=Dictionary(
                    elements={
                        "detect_proxy": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("Configure proxy server usage"),
                                help_text=Help(
                                    "By default, the Controller ignores proxy servers configured "
                                    "on the target system and connects directly (e.g. when querying "
                                    "the Agent Receiver port from the Checkmk REST API)."
                                ),
                                label=Label(
                                    "Detect and use proxies configured on the target system"
                                ),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "validate_api_cert": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title(
                                    "Configure TLS certificate validation for querying the "
                                    "Agent Receiver port from the Checkmk REST API"
                                ),
                                help_text=Help(
                                    "By default, certificate validation is disabled because it is not "
                                    "security-relevant at this stage, see "
                                    '<a href="https://checkmk.com/werk/14715" target="_blank">werk #14715</a>.'
                                ),
                                label=Label("Validate server certificate during port query"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="disabled",
                title=Title("Disable controller"),
                parameter_form=FixedValue(value=None),
            ),
        ),
    )


def migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "agent_ctl_enabled" not in value:
        return value
    ctl = value["agent_ctl_enabled"]
    # Old format: (True/False, opts) tuple
    if isinstance(ctl, (list, tuple)) and len(ctl) == 2 and isinstance(ctl[0], bool):
        enabled, opts = ctl[0], ctl[1]
        return {
            **value,
            "agent_ctl_enabled": (
                ("enabled", opts if opts is not None else {}) if enabled else ("disabled", None)
            ),
        }
    # Already migrated
    return value


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Agent Controller"),
        elements={
            "agent_ctl_enabled": DictElement(
                required=True,
                parameter_form=_agent_ctl_enabled_form(),
            ),
        },
        migrate=migrate,
    )


rule_spec_agent_controller = AgentConfig(
    name="agent_controller",
    title=Title("Agent Controller"),
    topic=Topic.WINDOWS,
    parameter_form=_parameter_form,
)
