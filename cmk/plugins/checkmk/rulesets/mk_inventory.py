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
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "deployment" in value:
        return value
    # Old rule ("first matching rule wins"): make all parameters explicit so that merging with
    # other rules does not change the outcome. An empty list means "no paths".
    return {
        "deployment": ("sync", None),
        "interval": value.get("interval", 14400.0),
        "exe_paths": value.get("exe_paths", []),
        "reg_paths": ("custom", value.get("reg_paths", [])),
    }


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "If you activate this option, the agent plug-in <tt>mk_inventory</tt> will be deployed"
            " on Linux and Windows hosts. It gathers information about installed hardware and"
            " software and makes the information available in graphical user interface (GUI) and"
            " for exporting to third-party software. <b>Note:</b> In order to actually use the"
            " inventory for a host you also need to enable it in the rule set"
            " <a href='wato.py?varname=active_checks%3Acmk_inv&folder=&mode=edit_ruleset'>"
            "Do HW/SW inventory</a>."
        ),
        migrate=migrate,
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
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
            "interval": DictElement(
                required=True,
                parameter_form=TimeSpan(
                    title=Title("Interval for collecting data"),
                    displayed_magnitudes=(
                        TimeMagnitude.DAY,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                    ),
                    prefill=DefaultValue(14400.0),
                ),
            ),
            "exe_paths": DictElement(
                parameter_form=List(
                    title=Title("Directories to search for <tt>EXE</tt> files (Windows)"),
                    element_template=String(
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                ),
            ),
            "reg_paths": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Registry Keys to search for software (Windows)"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="default",
                            title=Title("Search the standard uninstall keys"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "Searches <tt>Software\\Microsoft\\Windows\\CurrentVersion"
                                    "\\Uninstall</tt> and <tt>Software\\Wow6432Node\\Microsoft"
                                    "\\Windows\\CurrentVersion\\Uninstall</tt>, where Windows"
                                    " registers installed software."
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Title("Search the following registry keys"),
                            parameter_form=List(
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                        ),
                    ),
                    prefill=DefaultValue("default"),
                ),
            ),
        },
    )


rule_spec_mk_inventory = AgentConfig(
    title=Title("HW/SW inventory (Linux, Windows, Solaris, AIX)"),
    name="mk_inventory",
    topic=Topic.GENERAL,
    parameter_form=_form_spec,
)
