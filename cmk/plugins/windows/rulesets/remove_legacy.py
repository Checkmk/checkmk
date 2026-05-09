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
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value:
        return {"deployment": ("sync", None)}
    return {"deployment": ("do_not_deploy", None)}


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Enable this option if you want to uninstall the legacy agent "
            "after the new Windows agent have been installed."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Legacy agent management"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title(
                                "Uninstall the legacy (pre 1.6) agent after installation of the new Windows agent"
                            ),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not uninstall the legacy agent"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_remove_legacy = AgentConfig(
    title=Title("Legacy agent management (Windows)"),
    name="remove_legacy",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
