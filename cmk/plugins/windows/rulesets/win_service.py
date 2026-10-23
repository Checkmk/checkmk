#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _form_spec() -> Dictionary:
    return Dictionary(
        elements={
            "restart_on_crash": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Auto-restart on crash"),
                    help_text=Help(
                        "Use this rule set to enable or disable automatic service restarts on crash "
                        "or other internal errors."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="yes", title=Title("Windows Service restarts automatically")
                        ),
                        SingleChoiceElement(
                            name="no", title=Title("Windows Service doesn't restart automatically")
                        ),
                    ],
                    prefill=DefaultValue("yes"),
                ),
            ),
            "error_mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Action on error"),
                    help_text=Help(
                        "Use this rule set to control some actions which can be performed "
                        "upon crash or other problems."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="log",
                            title=Title("Windows Service writes information to the Event Log"),
                        ),
                        SingleChoiceElement(
                            name="ignore", title=Title("Windows Service does nothing")
                        ),
                    ],
                    prefill=DefaultValue("log"),
                ),
            ),
            "start_mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Service start type"),
                    help_text=Help(
                        "Use this rule set to choose a desirable start mode of the Windows "
                        "service. You may also prevent the service from starting."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="auto", title=Title("Windows Service starts automatically")
                        ),
                        SingleChoiceElement(
                            name="delayed",
                            title=Title("Windows Service starts automatically with delay"),
                        ),
                        SingleChoiceElement(
                            name="demand", title=Title("Windows Service starts on demand")
                        ),
                        SingleChoiceElement(
                            name="disabled",
                            title=Title("Windows Service is disabled and can't be started"),
                        ),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
        },
    )


rule_spec_win_service = AgentConfig(
    title=Title("Checkmk Windows agent service settings"),
    name="win_service",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
