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
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

_DEFAULT_MEGACLI_PATH = r"C:\Program Files\LSI Corporation\MegaCLI\MegaCli.exe"
_DEFAULT_TEMPDIR = r"C:\Temp"


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        result: dict[str, object] = {"deployment": ("sync", None)}
        result.update(value)
        return result
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in uses the command line tool MegaCli.exe in order to provide "
            "monitoring information of LSI RAID controllers and attached hard disks."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the MegaRAID plug-in"),
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
                            title=Title("Do not deploy the MegaRAID plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "megacli": DictElement(
                parameter_form=String(
                    title=Title("Path to MegaCLI.exe"),
                    prefill=DefaultValue(_DEFAULT_MEGACLI_PATH),
                ),
            ),
            "tempdir": DictElement(
                parameter_form=String(
                    title=Title("Path to temporary directory (will be created)"),
                    prefill=DefaultValue(_DEFAULT_TEMPDIR),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_win_megaraid = AgentConfig(
    title=Title("MegaRAID monitoring (Windows)"),
    name="win_megaraid",
    topic=Topic.STORAGE,
    parameter_form=_form_spec,
)
