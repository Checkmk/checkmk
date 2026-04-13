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
        dep = value["deployment"]
        if isinstance(dep, (tuple, list)) and dep[0] in ("sync", "cached", "do_not_deploy"):
            return value
        if isinstance(dep, (tuple, list)) and dep[0] == "smart_posix":
            return {"deployment": ("sync", None)}
        if isinstance(dep, (tuple, list)) and dep[0] == "smart":
            return {"deployment": ("sync", None), "use_legacy_plugin": True}
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if value == "smart_posix":
        return {"deployment": ("sync", None)}
    if value in ("smart", True):
        return {"deployment": ("sync", None), "use_legacy_plugin": True}
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_smart() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Hosts configured via this rule get the <tt>smart_posix</tt> or <tt>smart</tt> "
            "plug-in deployed. Assuming you have installed <tt>smartmontools</tt>, "
            "your local hard disks will be monitored for temperature and errors. "
            "The legacy plug-in <tt>smart</tt> is deprecated and should not be used anymore."
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
                            title=Title("Do not deploy the SMART plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "use_legacy_plugin": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Use deprecated legacy SMART plug-in (not recommended)"),
                    prefill=DefaultValue(False),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_smart = AgentConfig(
    title=Title("SMART hard disk monitoring (Linux)"),
    name="smart",
    topic=Topic.STORAGE,
    parameter_form=_valuespec_agent_config_smart,
)
