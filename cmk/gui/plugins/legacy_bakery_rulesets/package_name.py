#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "name" in value:
        return value
    if isinstance(value, str):
        return {"name": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Choose a custom name for the baked Checkmk agent package, other than default "
            "<tt>check-mk-agent</tt>. Please note that this rule only affects the name "
            "that is used by the package manager (e.g., RPM) to identify the Checkmk agent package, "
            "rather than the contents of the package, e.g., service names. "
            "In particular, it doesn't support to install multiple agents on one machine."
        ),
        migrate=migrate,
        # Consumed by the package builders (non-free cmk-bakery), not by a bakelet.
        elements={
            "name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Package name"),
                    prefill=DefaultValue("check-mk-agent"),
                    custom_validate=(
                        validators.MatchRegex(
                            "^[a-zA-Z][-a-zA-Z0-9]*$",
                            Message(
                                "A package must only consist of letters, digits, dash and it "
                                "must start with a letter."
                            ),
                        ),
                    ),
                ),
            ),
        },
    )


rule_spec_package_name = AgentConfig(
    title=Title("Name of agent packages (Linux, Unix)"),
    name="package_name",
    topic=Topic.LINUX,
    parameter_form=_form_spec,
)
