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


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        result: dict[str, object] = {"deployment": ("sync", None)}
        if "sqlserver" in value:
            result["sqlserver"] = value["sqlserver"]
        return result
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in monitors Arcserve backups by deploying a plug-in for the "
            "Arcserve server on Windows. This only supports the German version of "
            "Arcserve, since the log messages are in localized language."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the Arcserve plug-in"),
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
                            title=Title("Do not deploy the Arcserve plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "sqlserver": DictElement(
                parameter_form=String(
                    title=Title("SQL-Server to connect to"),
                    help_text=Help(r"Put the name of the database here, e.g. SATURN\ARCSERVE_DB"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_arcserve_backup = AgentConfig(
    title=Title("Arcserve (German) backups (Windows)"),
    name="arcserve_backup",
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec,
)
