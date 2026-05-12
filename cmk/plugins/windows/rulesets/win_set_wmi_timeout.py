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
    Integer,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "wmi_timeout" in value:
        return value
    if isinstance(value, int):
        return {"wmi_timeout": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Increase this value if WMI-based services are switching "
            "constantly into stale state. Default value is 3."
        ),
        elements={
            "wmi_timeout": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("WMI timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(3),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_win_set_wmi_timeout = AgentConfig(
    title=Title("Windows WMI Timeout"),
    name="win_set_wmi_timeout",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
