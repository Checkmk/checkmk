#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, list):
        return {"deployment": ("sync", None), "hostnames": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_dnsclient() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in tests the local DNS resolver by looking up one "
            "or several host names using <tt>nslookup</tt>. That tool is expected "
            "to be installed on the target machine."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy the plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "hostnames": DictElement(
                parameter_form=List(
                    title=Title("Host names to resolve"),
                    element_template=String(
                        custom_validate=(
                            validators.MatchRegex(
                                "^[-a-zA-Z0-9._]*$",
                                Message("Your host name has an invalid format."),
                            ),
                        ),
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_dnsclient = AgentConfig(
    title=Title("Local DNS resolving (Linux, Unix)"),
    name="dnsclient",
    topic=Topic.NETWORKING,
    parameter_form=_valuespec_agent_config_dnsclient,
)
