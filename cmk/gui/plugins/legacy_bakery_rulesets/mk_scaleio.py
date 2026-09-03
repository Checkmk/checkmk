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
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    match value:
        case None:
            return {"deployment": ("do_not_deploy", None)}
        case {"user": user, "password": password, "interval": int() | float() as interval}:
            # The old bakelet ran the plug-in synchronously for intervals of 60 seconds or less.
            return {
                "deployment": ("cached", float(interval)) if interval > 60 else ("sync", None),
                "user": user,
                "password": migrate_to_password(password),
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help("Deploy the agent plug-in <tt>mk_scaleio</tt> on your target system."),
        migrate=migrate,
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
                                ),
                                prefill=DefaultValue(60.0),
                            ),
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
            "user": DictElement(
                parameter_form=String(title=Title("Username")),
            ),
            "password": DictElement(
                parameter_form=Password(title=Title("Password")),
            ),
        },
    )


rule_spec_mk_scaleio = AgentConfig(
    title=Title("EMC ScaleIO"),
    name="mk_scaleio",
    topic=Topic.STORAGE,
    parameter_form=_form_spec,
)
