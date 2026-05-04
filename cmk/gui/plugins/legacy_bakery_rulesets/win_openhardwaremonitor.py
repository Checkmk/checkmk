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
    return {"deployment": ("sync", None)}


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Adds a headless version of the OpenHardwareMonitor to the Windows agent. "
            "The agent will then automatically use this to provide readings of hardware "
            "sensors (temperature, fans, ...) to Checkmk. "
            "This does require .Net to be installed on the target system. Please leave this "
            "disabled if you have a different way to monitor sensors. You also don't need "
            "this if you are running the regular OpenHardwareMonitor software."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy OpenHardwareMonitor (headless)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title(
                                "Deploy OpenHardwareMonitor (headless) and run asynchronously"
                            ),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                )
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy OpenHardwareMonitor (headless)"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_win_openhardwaremonitor = AgentConfig(
    title=Title("OpenHardwareMonitor (Windows)"),
    name="win_openhardwaremonitor",
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_form_spec,
)
