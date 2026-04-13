#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    SingleChoice,
    SingleChoiceElement,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "deployment" in value:
        return value
    interval = value["interval"]
    return {
        "deployment": ("cached", float(interval)) if interval else ("sync", None),
        "method": value["method"],
        "update": value["update"],
    }


def _valuespec_agent_config_mk_apt() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy the agent plug-in <tt>mk_apt</tt>. This will activate the "
            "check <tt>apt</tt> on DEB-based hosts (like Debian and Ubuntu) and monitor "
            "pending normal and security updates."
        ),
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
                                prefill=DefaultValue(24 * 3600),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("cached"),
                ),
            ),
            "method": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Method"),
                    elements=[
                        SingleChoiceElement(name="upgrade", title=Title("apt-get upgrade")),
                        SingleChoiceElement(
                            name="dist-upgrade", title=Title("apt-get dist-upgrade")
                        ),
                    ],
                    prefill=DefaultValue("upgrade"),
                ),
            ),
            "update": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Update package database"),
                    prefill=DefaultValue(True),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_apt = AgentConfig(
    title=Title("APT normal and security updates (Linux)"),
    name="mk_apt",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_valuespec_agent_config_mk_apt,
)
