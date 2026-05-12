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
    if isinstance(value, dict) and "cleanup_mode" in value:
        return value
    if isinstance(value, str):
        return {"cleanup_mode": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Choose what to do with the files under %PROGRAMDATA%\\checkmk on "
            "Checkmk agent uninstallation. Note: Uninstallation also happens on every "
            "agent update. Setting 'Remove all files and subdirectories' will break "
            "automatic agent updates and TLS encrypted agent communication, since the "
            "removed files include the agent updater and agent controller registrations."
        ),
        elements={
            "cleanup_mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("On Checkmk agent uninstallation"),
                    elements=[
                        SingleChoiceElement(
                            name="none",
                            title=Title("Do not remove anything"),
                        ),
                        SingleChoiceElement(
                            name="smart",
                            title=Title("Remove data managed by the Checkmk agent"),
                        ),
                        SingleChoiceElement(
                            name="all",
                            title=Title("Remove all files and subdirectories"),
                        ),
                    ],
                    prefill=DefaultValue("none"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_win_clean_uninstall = AgentConfig(
    title=Title("Clean up Checkmk agent program data directory on uninstall"),
    name="win_clean_uninstall",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
