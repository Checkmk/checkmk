#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "mode" in value:
        return value
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Windows Firewall"),
        elements={
            "mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Mode"),
                    help_text=Help(
                        "Use this rule set to automatically configure the firewall rules that are "
                        "needed to communicate with the Checkmk Windows agent on the monitored "
                        "Windows hosts."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="none",
                            title=Title("Do not configure Windows Firewall"),
                        ),
                        SingleChoiceElement(
                            name="remove",
                            title=Title("Remove Windows Firewall configuration if present"),
                        ),
                        SingleChoiceElement(
                            name="configure",
                            title=Title("Configure Windows Firewall to allow host monitoring"),
                        ),
                    ],
                    prefill=DefaultValue("configure"),
                ),
            ),
            "port": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Port"),
                    help_text=Help(
                        "This setting determines how ports will be enabled in Windows Firewall."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title("Required port"),
                        ),
                        SingleChoiceElement(
                            name="all",
                            title=Title("All ports"),
                        ),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_firewall = AgentConfig(
    title=Title("Windows Firewall"),
    name="firewall",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
