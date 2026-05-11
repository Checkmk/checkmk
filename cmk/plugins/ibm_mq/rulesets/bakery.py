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
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
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
        result: dict[str, object] = {"deployment": ("sync", None)}
        for key in ("only_qm", "skip_qm", "execute_as_another_user"):
            if key in value:
                result[key] = value[key]
        return result
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_ibm_mq() -> Dictionary:
    return Dictionary(
        help_text=Help("This plug-in monitors channels, managers and queues of IBM MQ."),
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
            "only_qm": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("Queues to monitor"),
                    help_text=Help("Only queues explicitly listed here will be monitored."),
                ),
            ),
            "skip_qm": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("Queues to be skipped"),
                    help_text=Help("All queues listed here will be skipped."),
                ),
            ),
            "execute_as_another_user": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Execute as another user"),
                    elements=[
                        SingleChoiceElement(name="mqm", title=Title("Execute as MQM")),
                    ],
                    prefill=DefaultValue("mqm"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_ibm_mq = AgentConfig(
    title=Title("IBM MQ (Linux)"),
    name="ibm_mq",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_ibm_mq,
)
