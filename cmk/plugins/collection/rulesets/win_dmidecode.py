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
    if isinstance(value, dict):
        return value
    return {"deployment": ("sync" if value else "do_not_deploy", None)}


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            r"This plug-in requires the executable <tt>C:\Programme\GnuWin32\sbin\dmidecode.exe</tt>. "
            "This is the default location when installing this tool. You can download it for free "
            "from <a href='http://gnuwin32.sourceforge.net/packages/dmidecode.htm'>here</a>."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy plug-in for Windows system info"),
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
                            title=Title("Do not deploy plug-in for Windows system info"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_win_dmidecode = AgentConfig(
    title=Title("System information for inventory via dmidecode (Windows)"),
    name="win_dmidecode",
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_form_spec,
)
