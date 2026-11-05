#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, String
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "user" in value:
        return value
    if isinstance(value, str):
        return {"user": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule set will only set the agent user to the configured value."
            "<br>It will not take care of further needed permissions on the target system."
            "<br>It applies only to hosts that match the rule <i>Use classic file deployment</i>."
            " All other hosts get the single directory deployment, where the agent runs as root"
            " unless the rule set <i>Customize agent package</i> configures another user."
            "<br>Please use <i>Customize agent package</i> instead, which offers a proper"
            " non-root agent installation.<br>"
        ),
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Linux user"),
                    prefill=DefaultValue("root"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_agent_user = AgentConfig(
    title=Title("Run agent as non-root user (Linux)"),
    name="agent_user",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_form_spec,
    is_deprecated=True,
)
