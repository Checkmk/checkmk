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
    if value in ("sequential", "parallel"):
        return {"mode": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help("This rulespec is deprecated and will be removed in future versions."),
        migrate=migrate,
        elements={
            "mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Asynchronous execution of plug-ins"),
                    elements=[
                        SingleChoiceElement(
                            name="sequential",
                            title=Title("Run asynchronous plug-ins sequential"),
                        ),
                        SingleChoiceElement(
                            name="parallel",
                            title=Title("Run asynchronous plug-ins in parallel"),
                        ),
                    ],
                    prefill=DefaultValue("sequential"),
                ),
            ),
        },
    )


rule_spec_win_script_async = AgentConfig(
    title=Title("Asynchronous execution of plug-ins (deprecated)"),
    name="win_script_async",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
    is_deprecated=True,
)
