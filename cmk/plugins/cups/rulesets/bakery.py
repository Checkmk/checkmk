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
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        interval = value["interval"]
        if isinstance(interval, (int, float)) and interval > 60:
            return {"deployment": ("cached", float(interval))}
        return {"deployment": ("sync", None)}
    raise ValueError(f"Unexpected value for mk_cups_queues migration: {value!r}")


def _valuespec_agent_config_mk_cups_queues() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy the agent plug-in <tt>mk_cups_queues</tt>"
            " to monitor CUPS printer queues on Linux."
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
                                )
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
        },
        migrate=migrate,
    )


rule_spec_mk_cups_queues = AgentConfig(
    title=Title("CUPS Printer Queues (Linux)"),
    name="mk_cups_queues",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_mk_cups_queues,
)
