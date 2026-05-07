#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        result: dict[str, object] = {"deployment": ("sync", None)}
        if "nvidia_smi_path" in value:
            result["nvidia_smi_path"] = value["nvidia_smi_path"]
        return result
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_nvidia_smi() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy the agent plug-in <tt>nvidia_smi</tt> used for monitoring Nvidia GPUs."
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
                                prefill=DefaultValue(24 * 3600.0),
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
            "nvidia_smi_path": DictElement(
                parameter_form=String(
                    title=Title("Path to nvidia-smi.exe (Windows only)"),
                    help_text=Help(
                        "Put the path to the nvidia-smi.exe executable here, e.g. "
                        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe. "
                        "Under Linux, the relevant executable is usually defined in the "
                        "PATH variable. Therefore, this setting is ignored under Linux."
                    ),
                    prefill=DefaultValue(
                        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
                    ),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_nvidia_smi = AgentConfig(
    title=Title("Nvidia GPU monitoring (Linux, Windows)"),
    name="nvidia_smi",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_valuespec_agent_config_nvidia_smi,
)
