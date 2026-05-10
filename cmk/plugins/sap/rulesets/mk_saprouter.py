#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
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
    if isinstance(value, dict):
        interval = value.get("interval", 0)
        deployment: tuple[str, object] = (
            ("cached", float(interval))
            if isinstance(interval, (int, float)) and interval > 60
            else ("sync", None)
        )
        result: dict[str, object] = {"deployment": deployment}
        for key in ("user", "path"):
            if key in value:
                result[key] = value[key]
        return result
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_mk_saprouter() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy and configure the Checkmk agent plug-in mk_saprouter. "
            "The plug-in runs below the specified user's environment. Furthermore you have to "
            "determine the path to sapgenpse. It's recommended to run the plug-in asynchronously."
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
                                    TimeMagnitude.DAY,
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(86400.0),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("cached"),
                ),
            ),
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "path": DictElement(
                parameter_form=String(
                    title=Title("Path to sapgenpse"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_saprouter = AgentConfig(
    title=Title("SAP router certificate"),
    name="mk_saprouter",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_mk_saprouter,
)
