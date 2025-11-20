#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _validate_at_least_one_plugin(value: Sequence[str]) -> object:
    """Validate that at least one Hyper-V plugin is selected"""
    if not value or len(value) == 0:
        raise validators.ValidationError(
            message=Message(
                "At least one Hyper-V monitoring component must be selected. "
                "Please choose from the available monitoring options."
            )
        )
    return value


def _valuespec_agent_config_hyperv_collection() -> Dictionary:
    return Dictionary(
        elements={
            "deploy": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment"),
                    prefill=DefaultValue("deploy"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="deploy",
                            title=Title("Deploy Hyper-V monitoring plug-ins"),
                            parameter_form=MultipleChoice(
                                title=Title("Hyper-V monitoring components"),
                                help_text=Help(
                                    "Select which Hyper-V plug-ins should be deployed. "
                                    "Each plug-in monitors specific aspects of your Hyper-V infrastructure."
                                ),
                                elements=(
                                    MultipleChoiceElement(
                                        name="hyperv_host",
                                        title=Title("Hyper-V Host monitoring"),
                                    ),
                                ),
                                prefill=DefaultValue(["hyperv_host"]),
                                custom_validate=[_validate_at_least_one_plugin],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy Hyper-V plug-ins"),
                            parameter_form=FixedValue(
                                title=Title("Do not deploy Hyper-V plug-ins"),
                                label=Label("(disabled)"),
                                value=None,
                            ),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_AgentConfig = AgentConfig(
    title=Title("Hyper-V"),
    name="hyperv_collection",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_hyperv_collection,
    help_text=Help("This will deploy Hyper-V monitoring plug-ins on your target system."),
)
