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
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value == "ps1":
        return {"deployment": ("sync", None), "use_bat_plugin": False}
    if value == "bat":
        return {"deployment": ("sync", None), "use_bat_plugin": True}
    if value is False:
        return {"deployment": ("do_not_deploy", None)}
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in checks the status and performance of network interfaces on Windows. "
            "Use the legacy plug-in for Windows versions without Powershell."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy plug-in for Windows interfaces"),
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
                            title=Title("Do not deploy plug-in for Windows interfaces"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "use_bat_plugin": DictElement(
                parameter_form=BooleanChoice(
                    label=Label(
                        "Use legacy batch file plug-in (wmic_if.bat) instead of PowerShell plug-in"
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_winperf_if = AgentConfig(
    title=Title("Network interfaces on Windows"),
    name="winperf_if",
    topic=Topic.NETWORKING,
    parameter_form=_form_spec,
)
