#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue, DictElement, Dictionary
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _form_spec() -> Dictionary:
    return Dictionary(
        elements={
            "use_wmi": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Use WMI"),
                    label=Label(
                        "Retrieve process information using WMI (Windows Management Instrumentation)"
                    ),
                    help_text=Help(
                        "Rely on WMI (Windows Management Instrumentation) when retrieving process "
                        "information. Using WMI is mandatory for including the full path of a running "
                        "process in the list of processes."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "full_path": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Include full path"),
                    label=Label(
                        "Include the full path of a process and its arguments in the process list. "
                        "Note: this requires using WMI for retrieving process information."
                    ),
                    help_text=Help(
                        "Include the full path of a process and its arguments in the process list. "
                        "Note: this requires using WMI for retrieving process information."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_win_ps = AgentConfig(
    title=Title("Fine-tune Windows process monitoring"),
    name="win_ps",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
